package vip.qimono.proxora.mcp

import io.modelcontextprotocol.kotlin.sdk.server.StdioServerTransport
import kotlinx.coroutines.Job
import kotlinx.coroutines.runBlocking
import kotlinx.io.asSink
import kotlinx.io.asSource
import kotlinx.io.buffered
import vip.qimono.proxora.mcp.engine.EngineClient
import vip.qimono.proxora.mcp.engine.EngineCommand

/**
 * Runs the PROXORA MCP server over stdio, the transport MCP clients use when
 * they launch a local server. stdout carries only MCP messages; logs and the
 * Python engine's own output go to stderr.
 */
fun main() {
    EngineClient(EngineCommand.fromEnvironment()).use { engine ->
        val server = ProxoraServer.create(engine)
        val transport = StdioServerTransport(
            input = System.`in`.asSource().buffered(),
            output = System.out.asSink().buffered(),
        )
        runBlocking {
            val session = server.createSession(transport)
            val done = Job()
            session.onClose { done.complete() }
            done.join()
        }
    }
}
