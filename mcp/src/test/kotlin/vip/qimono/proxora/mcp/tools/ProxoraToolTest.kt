package vip.qimono.proxora.mcp.tools

import io.modelcontextprotocol.kotlin.sdk.types.TextContent
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.double
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonArray
import kotlinx.serialization.json.JsonPrimitive
import vip.qimono.proxora.mcp.ProxoraServer
import vip.qimono.proxora.mcp.engine.Engine
import vip.qimono.proxora.mcp.engine.EngineClient
import vip.qimono.proxora.mcp.engine.EngineCommand
import vip.qimono.proxora.mcp.engine.EngineException
import kotlin.test.Test
import kotlin.test.assertContains
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** An engine that answers from a script, recording what it was asked. */
private class FakeEngine(private val answer: (String, String) -> String) : Engine {
    val calls = mutableListOf<Pair<String, String>>()

    override fun request(tool: String, argumentsJson: String): String {
        calls += tool to argumentsJson
        return answer(tool, argumentsJson)
    }
}

class ProxoraToolTest {
    private val series = buildJsonObject { putJsonArray("values") { listOf(1, 3, 5, 7).forEach { add(JsonPrimitive(it)) } } }

    @Test
    fun `missing required arguments never reach the engine`() = runTest {
        val engine = FakeEngine { _, _ -> error("must not be called") }
        val result = ScoreForecastTool().call(engine, buildJsonObject { put("actual", 1.0) })
        assertEquals(true, result.isError)
        assertContains((result.content.single() as TextContent).text, "forecast")
        assertTrue(engine.calls.isEmpty())
    }

    @Test
    fun `a successful reply becomes text plus structured content`() = runTest {
        val engine = FakeEngine { _, _ -> """{"id":1,"ok":true,"result":{"value":9.0}}""" }
        val result = PredictNextTool().call(engine, series)
        assertNull(result.isError)
        assertEquals(9.0, result.structuredContent!!["value"]!!.jsonPrimitive.double)
        assertEquals("predict_next", engine.calls.single().first)
    }

    @Test
    fun `an engine error becomes an error result`() = runTest {
        val engine = FakeEngine { _, _ -> """{"id":1,"ok":false,"error":"ValueError: too short"}""" }
        val result = PredictNextTool().call(engine, series)
        assertEquals(true, result.isError)
        assertEquals("ValueError: too short", (result.content.single() as TextContent).text)
    }

    @Test
    fun `an unreachable engine becomes an error result`() = runTest {
        val engine = FakeEngine { _, _ -> throw EngineException("engine down") }
        val result = BacktestTool().call(engine, series)
        assertEquals(true, result.isError)
    }

    @Test
    fun `every required argument is a declared property`() {
        for (tool in ProxoraServer.defaultTools()) {
            val properties = assertNotNull(tool.inputSchema.properties)
            for (name in tool.inputSchema.required.orEmpty()) {
                assertTrue(name in properties, "${tool.name}: '$name' is required but not declared")
            }
        }
    }

    @Test
    fun `tool names are unique`() {
        val names = ProxoraServer.defaultTools().map { it.name }
        assertEquals(names.size, names.toSet().size)
    }

    @Test
    fun `end to end through the real Python engine`() = runTest {
        EngineClient(EngineCommand.fromEnvironment()).use { engine ->
            val result = PredictNextTool().call(engine, series)
            assertNull(result.isError)
            assertEquals(9.0, result.structuredContent!!["value"]!!.jsonPrimitive.double)
        }
    }
}
