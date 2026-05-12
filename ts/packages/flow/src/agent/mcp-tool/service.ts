/**
 * MCP tool-calling service — calls external MCP tool servers.
 *
 * Receives ToolRequest (name + JSON-encoded parameters) over NATS,
 * connects to the appropriate MCP server via the MCP SDK,
 * invokes the tool, and returns the result as a ToolResponse.
 *
 * MCP service configs are pushed via the config system under the "mcp" key.
 *
 * Python reference: trustgraph-flow/trustgraph/agent/mcp_tool/service.py
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

import {
  FlowProcessor,
  ConsumerSpec,
  ProducerSpec,
  type ProcessorConfig,
  type FlowContext,
  type ToolRequest,
  type ToolResponse,
} from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";

interface McpServiceConfig {
  url: string;
  "remote-name"?: string;
  "auth-token"?: string;
}

export class McpToolService extends FlowProcessor {
  private mcpServices: Record<string, McpServiceConfig> = {};

  constructor(config: ProcessorConfig) {
    super(config);

    this.registerSpecification(
      ConsumerSpec.fromPromise<ToolRequest>("mcp-tool-request", this.onRequest.bind(this)),
    );
    this.registerSpecification(new ProducerSpec<ToolResponse>("mcp-tool-response"));

    this.registerConfigHandler(this.onMcpConfig.bind(this));
  }

  private async onMcpConfig(
    config: Record<string, unknown>,
    version: number,
  ): Promise<void> {
    console.log(`[McpToolService] Got config version ${version}`);

    if (!("mcp" in config) || typeof config.mcp !== "object" || config.mcp === null) {
      this.mcpServices = {};
      return;
    }

    const mcpConfig = config.mcp as Record<string, string>;
    this.mcpServices = {};

    for (const [name, value] of Object.entries(mcpConfig)) {
      try {
        this.mcpServices[name] = JSON.parse(value) as McpServiceConfig;
        console.log(`[McpToolService] Registered MCP service: ${name}`);
      } catch (err) {
        console.error(`[McpToolService] Failed to parse MCP config for ${name}:`, err);
      }
    }

    console.log(
      `[McpToolService] ${Object.keys(this.mcpServices).length} MCP services configured`,
    );
  }

  private async onRequest(
    msg: ToolRequest,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (requestId === undefined || requestId.length === 0) return;

    const responseProducer = flowCtx.flow.producer<ToolResponse>("mcp-tool-response");

    try {
      const result = await this.invokeTool(
        msg.name,
        msg.parameters !== undefined && msg.parameters.length > 0
          ? JSON.parse(msg.parameters) as Record<string, unknown>
          : {},
      );

      if (typeof result === "string") {
        await responseProducer.send(requestId, { text: result });
      } else {
        await responseProducer.send(requestId, { object: JSON.stringify(result) });
      }
    } catch (err) {
      console.error(`[McpToolService] Error invoking tool ${msg.name}:`, err);
      const message = err instanceof Error ? err.message : String(err);
      await responseProducer.send(requestId, {
        error: { type: "tool-error", message },
      });
    }
  }

  private async invokeTool(
    name: string,
    parameters: Record<string, unknown>,
  ): Promise<string | unknown> {
    if (!(name in this.mcpServices)) {
      throw new Error(`MCP service "${name}" not known`);
    }

    const svcConfig = this.mcpServices[name];
    if (svcConfig.url.length === 0) {
      throw new Error(`MCP service "${name}" URL not defined`);
    }

    const remoteName = svcConfig["remote-name"] ?? name;

    // Build headers with optional bearer token
    const headers: Record<string, string> = {};
    if (svcConfig["auth-token"] !== undefined && svcConfig["auth-token"].length > 0) {
      headers["Authorization"] = `Bearer ${svcConfig["auth-token"]}`;
    }

    console.log(`[McpToolService] Invoking ${remoteName} at ${svcConfig.url}`);

    // Connect to streamable HTTP MCP server
    const transport = new StreamableHTTPClientTransport(
      new URL(svcConfig.url),
      { requestInit: { headers } },
    );

    const client = new Client({ name: "trustgraph-mcp-client", version: "1.0.0" });

    try {
      await client.connect(transport as unknown as Parameters<Client["connect"]>[0]);

      const result = await client.callTool({
        name: remoteName,
        arguments: parameters,
      });

      // Extract response — prefer structured content, fall back to text
      if (result.structuredContent !== undefined && result.structuredContent !== null) {
        return result.structuredContent;
      }

      if (result.content !== undefined && Array.isArray(result.content)) {
        return result.content
          .filter((c): c is { type: "text"; text: string } => c.type === "text")
          .map((c) => c.text)
          .join("");
      }

      return "No content";
    } finally {
      await transport.close();
    }
  }
}

export const program = makeProcessorProgram({
  id: "mcp-tool",
  make: (config) => new McpToolService(config),
});
