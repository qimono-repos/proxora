package vip.qimono.proxora.mcp.tools

import io.modelcontextprotocol.kotlin.sdk.types.ToolSchema
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** Next value of a series, classical or quantum, as a point plus a range. */
class PredictNextTool : ProxoraTool(
    name = "predict_next",
    description = """
        Predict the next value of an evenly spaced series (oldest first) as a point plus a range.
        method 'lr': least-squares line on the time index with a classical prediction interval.
        method 'qu': variational quantum regressor (one qubit per lag, data re-uploading layers,
        <Z> readout, classical optimiser). lags, layers, seed, backend and target apply only to 'qu'.
    """.trimIndent(),
) {
    override val inputSchema = ToolSchema(
        properties = buildJsonObject {
            put("values", Schemas.arrayOf(Schemas.number("A value of the series."), "The series, oldest first.", minItems = 2))
            put("method", Schemas.string("'lr' least squares or 'qu' quantum regressor.", listOf("lr", "qu"), default = "lr"))
            put("confidence", Schemas.number("Confidence level of the range, e.g. 0.9.", minimum = 0.5, maximum = 0.999))
            put("lags", Schemas.integer("qu only: past values used as inputs (one qubit each). Default 2.", minimum = 1))
            put("layers", Schemas.integer("qu only: data re-uploading layers. Default 2.", minimum = 1))
            put("seed", Schemas.integer("qu only: random seed for reproducible training. Default 42."))
            put("backend", Schemas.string("qu only: circuit simulator.", listOf("numpy", "qiskit"), default = "numpy"))
            put("target", Schemas.string("qu only: learn step changes or levels.", listOf("diff", "level"), default = "diff"))
        },
        required = listOf("values"),
    )
}
