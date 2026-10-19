plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.shadow)
    application
}

group = "vip.qimono.proxora"
version = "0.2.0"

application {
    mainClass.set("vip.qimono.proxora.mcp.MainKt")
}

dependencies {
    implementation(libs.mcp.kotlin.server)
    // MCP over stdio: logs must go to stderr, never stdout. slf4j-simple does that by default.
    implementation(libs.slf4j.simple)

    testImplementation(kotlin("test"))
    testImplementation(libs.kotlinx.coroutines.test)
}

kotlin {
    jvmToolchain(21)
}

tasks.test {
    useJUnitPlatform()
    // The engine tests start the real Python engine. Point them at it from the repo layout.
    environment("PROXORA_ENGINE_DIR", rootProject.projectDir.resolve("../python").canonicalPath)
}
