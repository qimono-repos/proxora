package vip.qimono.proxora.mcp

import io.modelcontextprotocol.kotlin.sdk.server.Server
import io.modelcontextprotocol.kotlin.sdk.server.ServerOptions
import io.modelcontextprotocol.kotlin.sdk.types.Implementation
import io.modelcontextprotocol.kotlin.sdk.types.ServerCapabilities
import vip.qimono.proxora.mcp.engine.Engine
import vip.qimono.proxora.mcp.tools.BacktestTool
import vip.qimono.proxora.mcp.tools.PredictNextTool
import vip.qimono.proxora.mcp.tools.ProxoraTool
import vip.qimono.proxora.mcp.tools.ScoreBatchTool
import vip.qimono.proxora.mcp.tools.ScoreForecastTool

/** Builds the PROXORA MCP server: the SDK [Server] with every [ProxoraTool] registered. */
object ProxoraServer {
    const val VERSION = "0.2.0"

    val INSTRUCTIONS = """
        PROXORA predicts the next value of a series and scores forecasts.
        Forecasts are a point plus a range [low, high]. Score them with SPE =
        ((actual - forecast) / actual)^2 and aggregate with MSPE / RMSPE, which are
        comparable across assets of any price. A range works like an SVR epsilon tube:
        misses inside it cost nothing. Compare 'lr' and 'qu' with backtest before
        trusting either; no quantum advantage is assumed.
    """.trimIndent()

    fun defaultTools(): List<ProxoraTool> =
        listOf(ScoreForecastTool(), ScoreBatchTool(), PredictNextTool(), BacktestTool())

    fun create(engine: Engine, tools: List<ProxoraTool> = defaultTools()): Server {
        val server = Server(
            Implementation(name = "proxora", version = VERSION),
            ServerOptions(capabilities = ServerCapabilities(tools = ServerCapabilities.Tools(listChanged = false))),
            INSTRUCTIONS,
        )
        for (tool in tools) {
            server.addTool(
                name = tool.name,
                description = tool.description,
                inputSchema = tool.inputSchema,
                toolAnnotations = tool.annotations,
            ) { request -> tool.call(engine, request.arguments) }
        }
        return server
    }
}
