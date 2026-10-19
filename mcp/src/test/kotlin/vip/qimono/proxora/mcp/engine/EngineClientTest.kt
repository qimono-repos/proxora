package vip.qimono.proxora.mcp.engine

import kotlin.test.AfterTest
import kotlin.test.Test
import kotlin.test.assertContains
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

/** Talks to the real Python engine (PROXORA_ENGINE_DIR is set by build.gradle.kts). */
class EngineClientTest {
    private val client = EngineClient(EngineCommand.fromEnvironment())

    @AfterTest
    fun tearDown() = client.close()

    @Test
    fun `predicts the clojure example through the bridge`() {
        val reply = client.request("predict_next", """{"values":[1,3,5,7]}""")
        assertContains(reply, "\"ok\": true")
        assertContains(reply, "\"value\": 9.0")
    }

    @Test
    fun `engine errors come back as data`() {
        val reply = client.request("no_such_tool", "{}")
        assertContains(reply, "\"ok\": false")
        assertContains(reply, "Unknown tool")
    }

    @Test
    fun `reuses one process across requests`() {
        client.request("ping", "{}")
        assertTrue(client.isRunning)
        repeat(3) { assertContains(client.request("ping", "{}"), "\"ok\": true") }
    }

    @Test
    fun `restarts after the engine was stopped`() {
        client.request("ping", "{}")
        client.close()
        assertContains(client.request("ping", "{}"), "\"ok\": true")
    }

    @Test
    fun `a command that cannot start is an EngineException`() {
        val broken = EngineClient(EngineCommand(listOf("/nonexistent/proxora-engine")))
        assertFailsWith<EngineException> { broken.request("ping", "{}") }
    }

    @Test
    fun `quote escapes JSON special characters`() {
        assertEquals("\"a\\\"b\\\\c\\n\"", EngineClient.quote("a\"b\\c\n"))
    }
}
