import { supabase } from '../supabase';
import { globalEventBus } from '../eventBus';
import { TrivariateHashGenerator } from '../trivariate';
import { getGLAFBridge } from '../glaf/globalBridge';
import {
  Workflow,
  WorkflowExecution,
  WorkflowNode,
  WorkflowEdge,
  NodeExecutionContext,
  NodeExecutionResult,
  DAGValidationResult,
  ExecutionPlan,
  ExecutionStep
} from '../../types/workflow.types';

export class WorkflowExecutor {
  private executionId: string | null = null;
  private nodeResults: Map<string, any> = new Map();

  async validateWorkflow(workflow: Workflow): Promise<DAGValidationResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (!workflow.definition.nodes || workflow.definition.nodes.length === 0) {
      errors.push('Workflow must have at least one node');
    }

    const cycles = this.detectCycles(workflow.definition.nodes, workflow.definition.edges);
    if (cycles.length > 0) {
      errors.push(`Workflow contains cycles: ${cycles.map(c => c.join(' -> ')).join(', ')}`);
    }

    const unreachableNodes = this.findUnreachableNodes(
      workflow.definition.nodes,
      workflow.definition.edges
    );
    if (unreachableNodes.length > 0) {
      warnings.push(`Found ${unreachableNodes.length} unreachable nodes`);
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
      cycles: cycles.length > 0 ? cycles : undefined,
      unreachableNodes: unreachableNodes.length > 0 ? unreachableNodes : undefined
    };
  }

  private detectCycles(
    nodes: WorkflowNode[],
    edges: WorkflowEdge[]
  ): string[][] {
    const graph = new Map<string, string[]>();
    nodes.forEach(node => graph.set(node.id, []));
    edges.forEach(edge => {
      const targets = graph.get(edge.source_node_id) || [];
      targets.push(edge.target_node_id);
      graph.set(edge.source_node_id, targets);
    });

    const cycles: string[][] = [];
    const visited = new Set<string>();
    const recursionStack = new Set<string>();
    const path: string[] = [];

    const dfs = (nodeId: string): boolean => {
      visited.add(nodeId);
      recursionStack.add(nodeId);
      path.push(nodeId);

      const neighbors = graph.get(nodeId) || [];
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          if (dfs(neighbor)) return true;
        } else if (recursionStack.has(neighbor)) {
          const cycleStart = path.indexOf(neighbor);
          cycles.push(path.slice(cycleStart));
          return true;
        }
      }

      path.pop();
      recursionStack.delete(nodeId);
      return false;
    };

    for (const nodeId of graph.keys()) {
      if (!visited.has(nodeId)) {
        dfs(nodeId);
      }
    }

    return cycles;
  }

  private findUnreachableNodes(
    nodes: WorkflowNode[],
    edges: WorkflowEdge[]
  ): string[] {
    const triggerNodes = nodes.filter(n => n.category === 'trigger');
    if (triggerNodes.length === 0) return [];

    const reachable = new Set<string>();
    const queue = triggerNodes.map(n => n.id);

    while (queue.length > 0) {
      const current = queue.shift()!;
      if (reachable.has(current)) continue;
      reachable.add(current);

      const outgoingEdges = edges.filter(e => e.source_node_id === current);
      outgoingEdges.forEach(edge => {
        if (!reachable.has(edge.target_node_id)) {
          queue.push(edge.target_node_id);
        }
      });
    }

    return nodes.filter(n => !reachable.has(n.id)).map(n => n.id);
  }

  async buildExecutionPlan(workflow: Workflow): Promise<ExecutionPlan> {
    const nodes = workflow.definition.nodes;
    const edges = workflow.definition.edges;

    const inDegree = new Map<string, number>();
    const dependencies = new Map<string, string[]>();

    nodes.forEach(node => {
      inDegree.set(node.id, 0);
      dependencies.set(node.id, []);
    });

    edges.forEach(edge => {
      const current = inDegree.get(edge.target_node_id) || 0;
      inDegree.set(edge.target_node_id, current + 1);

      const deps = dependencies.get(edge.target_node_id) || [];
      deps.push(edge.source_node_id);
      dependencies.set(edge.target_node_id, deps);
    });

    const steps: ExecutionStep[] = [];
    const parallelGroups: string[][] = [];
    let currentLevel: string[] = [];

    nodes.forEach(node => {
      if (inDegree.get(node.id) === 0) {
        currentLevel.push(node.id);
      }
    });

    while (currentLevel.length > 0) {
      parallelGroups.push([...currentLevel]);

      currentLevel.forEach(nodeId => {
        steps.push({
          nodeId,
          dependencies: dependencies.get(nodeId) || [],
          canRunInParallel: currentLevel.length > 1,
          estimatedDuration: 1000
        });
      });

      const nextLevel: string[] = [];
      edges
        .filter(edge => currentLevel.includes(edge.source_node_id))
        .forEach(edge => {
          const newDegree = (inDegree.get(edge.target_node_id) || 1) - 1;
          inDegree.set(edge.target_node_id, newDegree);

          if (newDegree === 0 && !nextLevel.includes(edge.target_node_id)) {
            nextLevel.push(edge.target_node_id);
          }
        });

      currentLevel = nextLevel;
    }

    return {
      steps,
      parallelGroups,
      estimatedDuration: steps.reduce((sum, step) => sum + step.estimatedDuration, 0)
    };
  }

  async executeWorkflow(
    workflowId: string,
    inputData: Record<string, any> = {},
    triggeredBy?: string
  ): Promise<WorkflowExecution> {
    this.nodeResults.clear();

    const { data: workflow, error: workflowError } = await supabase
      .from('workflows')
      .select('*')
      .eq('id', workflowId)
      .maybeSingle();

    if (workflowError || !workflow) {
      throw new Error(`Workflow not found: ${workflowId}`);
    }

    const validation = await this.validateWorkflow(workflow as Workflow);
    if (!validation.valid) {
      throw new Error(`Invalid workflow: ${validation.errors.join(', ')}`);
    }

    const { data: execution, error: executionError } = await supabase
      .from('workflow_executions')
      .insert({
        workflow_id: workflowId,
        status: 'running',
        triggered_by: triggeredBy,
        input_data: inputData,
        started_at: new Date().toISOString()
      })
      .select()
      .single();

    if (executionError || !execution) {
      throw new Error('Failed to create execution record');
    }

    this.executionId = execution.id;

    globalEventBus.emit('workflow:execution:started', {
      workflowId,
      executionId: execution.id,
      triggeredBy
    });

    try {
      const plan = await this.buildExecutionPlan(workflow as Workflow);
      const result = await this.executePlan(workflow as Workflow, plan, inputData);

      const { error: updateError } = await supabase
        .from('workflow_executions')
        .update({
          status: 'completed',
          result_data: result,
          completed_at: new Date().toISOString()
        })
        .eq('id', execution.id);

      if (updateError) {
        console.error('Failed to update execution:', updateError);
      }

      globalEventBus.emit('workflow:execution:completed', {
        workflowId,
        executionId: execution.id,
        result
      });

      return { ...execution, status: 'completed', result_data: result } as WorkflowExecution;
    } catch (error: any) {
      const { error: updateError } = await supabase
        .from('workflow_executions')
        .update({
          status: 'failed',
          error_data: {
            message: error.message,
            stack: error.stack
          },
          completed_at: new Date().toISOString()
        })
        .eq('id', execution.id);

      if (updateError) {
        console.error('Failed to update execution:', updateError);
      }

      globalEventBus.emit('workflow:execution:failed', {
        workflowId,
        executionId: execution.id,
        error: error.message
      });

      throw error;
    }
  }

  private async executePlan(
    workflow: Workflow,
    plan: ExecutionPlan,
    inputData: Record<string, any>
  ): Promise<Record<string, any>> {
    for (const group of plan.parallelGroups) {
      const promises = group.map(nodeId => {
        const node = workflow.definition.nodes.find(n => n.id === nodeId);
        if (!node) {
          throw new Error(`Node not found: ${nodeId}`);
        }
        return this.executeNode(workflow, node, inputData);
      });

      const results = await Promise.all(promises);
      results.forEach((result, index) => {
        this.nodeResults.set(group[index], result.output);
      });
    }

    return Object.fromEntries(this.nodeResults);
  }

  private async executeNode(
    workflow: Workflow,
    node: WorkflowNode,
    workflowInput: Record<string, any>
  ): Promise<NodeExecutionResult> {
    const startTime = Date.now();

    await this.logNodeExecution(node, 'running');

    try {
      const bridge = getGLAFBridge();
      const unicode = bridge.registerWorkflowNode(node);

      const inputEdges = workflow.definition.edges.filter(
        e => e.target_node_id === node.id
      );

      const nodeInput: Record<string, any> = {};
      inputEdges.forEach(edge => {
        const sourceOutput = this.nodeResults.get(edge.source_node_id);
        if (sourceOutput !== undefined) {
          nodeInput[edge.target_port] = sourceOutput;
        }
      });

      const context: NodeExecutionContext = {
        workflowId: workflow.id,
        executionId: this.executionId!,
        nodeId: node.id,
        input: Object.keys(nodeInput).length > 0 ? nodeInput : workflowInput,
        config: node.node_config,
        context: {
          workflow,
          execution: {} as any,
          previousNodes: Object.fromEntries(this.nodeResults)
        }
      };

      bridge.recordExecution(node.id, context);

      const result = await this.executeNodeType(node.node_type, context);

      bridge.recordSuccess(unicode, result);

      const latency = Date.now() - startTime;

      await this.logNodeExecution(node, 'completed', result, latency);

      console.log(`[GLAF] Node ${node.id} completed (U+${unicode.toString(16).toUpperCase()}, ${latency}ms)`);

      return {
        success: true,
        output: result,
        metadata: {
          latency_ms: latency,
          retry_count: 0,
          glaf_unicode: unicode
        }
      };
    } catch (error: any) {
      const latency = Date.now() - startTime;

      const bridge = getGLAFBridge();
      const unicode = bridge.getNodeUnicode(node.id);
      if (unicode) {
        bridge.recordFailure(unicode, error);
      }

      await this.logNodeExecution(node, 'failed', undefined, latency, error);

      return {
        success: false,
        error: {
          message: error.message,
          code: error.code,
          details: error
        },
        metadata: {
          latency_ms: latency,
          retry_count: 0
        }
      };
    }
  }

  private async executeNodeType(
    nodeType: string,
    context: NodeExecutionContext
  ): Promise<any> {
    const handlers: Record<string, (ctx: NodeExecutionContext) => Promise<any>> = {
      trigger_manual: async () => context.input,
      data_supabase_query: async (ctx) => {
        const { table, columns, filters, limit } = ctx.config;
        let query = supabase.from(table).select(columns || '*');

        if (filters && Array.isArray(filters)) {
          filters.forEach((filter: any) => {
            query = (query as any)[filter.operator](filter.column, filter.value);
          });
        }

        if (limit) {
          query = query.limit(limit);
        }

        const { data, error } = await query;
        if (error) throw error;
        return { data, count: data?.length || 0 };
      },
      data_entity_lookup: async (ctx) => {
        const identifier = ctx.input.identifier;
        const lookupType = ctx.config.lookupType || 'trivariate_hash';

        const { data, error } = await supabase
          .from('entities')
          .select('*')
          .eq(lookupType, identifier)
          .maybeSingle();

        if (error) throw error;
        return { entity: data };
      },
      transform_trivariate: async (ctx) => {
        const hash = TrivariateHashGenerator.generate(JSON.stringify(ctx.input));
        const parts = TrivariateHashGenerator.parseTrivariate(hash);
        return { hash, sch: parts.sch, cuid: parts.cuid, uuid: parts.uuid };
      },
      action_create_entity: async (ctx) => {
        const entityData = {
          ...ctx.input.entity,
          entity_type: ctx.config.entityType,
          trivariate_hash: ctx.config.autoGenerateHash
            ? TrivariateHashGenerator.generate(JSON.stringify(ctx.input.entity))
            : ctx.input.entity.trivariate_hash
        };

        const { data, error } = await supabase
          .from('entities')
          .insert(entityData)
          .select()
          .single();

        if (error) throw error;
        return { entityId: data.id, trivariateHash: data.trivariate_hash };
      },
      action_emit_event: async (ctx) => {
        globalEventBus.emit(ctx.config.eventType, ctx.input.data);
        return { success: true };
      },
      control_delay: async (ctx) => {
        await new Promise(resolve => setTimeout(resolve, ctx.config.duration));
        return ctx.input.input;
      },
      output_log: async (ctx) => {
        console.log(`[${ctx.config.level || 'info'}]`, ctx.input.message);
        return { logged: true };
      }
    };

    const handler = handlers[nodeType];
    if (!handler) {
      return { output: `Node type ${nodeType} not implemented yet` };
    }

    return await handler(context);
  }

  private async logNodeExecution(
    node: WorkflowNode,
    status: string,
    output?: any,
    latency?: number,
    error?: any
  ) {
    if (!this.executionId) return;

    await supabase.from('workflow_execution_logs').insert({
      execution_id: this.executionId,
      node_id: node.id,
      node_key: node.node_key,
      node_type: node.node_type,
      status,
      output_data: output,
      error_data: error ? { message: error.message, stack: error.stack } : undefined,
      latency_ms: latency,
      completed_at: status === 'completed' || status === 'failed' ? new Date().toISOString() : undefined
    });
  }
}

export const workflowExecutor = new WorkflowExecutor();
