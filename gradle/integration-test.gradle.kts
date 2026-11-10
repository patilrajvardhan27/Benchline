// Shared by the Spring apps: adds an `integrationTest` source set and task.
// Integration tests need a database (Testcontainers, or TEST_DATABASE_URL) and
// an embedded Kafka broker, so they stay out of the fast `test` task.
val sourceSets = extensions.getByType<SourceSetContainer>()
val main = sourceSets.getByName("main")
val test = sourceSets.getByName("test")

val integrationTest = sourceSets.create("integrationTest") {
    compileClasspath += main.output + test.output
    runtimeClasspath += main.output + test.output
    // Flyway reads the same migrations the deploy job runs: classpath:migrations
    resources.srcDir(rootProject.file("db"))
}

configurations.getByName("integrationTestImplementation")
    .extendsFrom(configurations.getByName("testImplementation"))
configurations.getByName("integrationTestRuntimeOnly")
    .extendsFrom(configurations.getByName("testRuntimeOnly"))

tasks.register<Test>("integrationTest") {
    description = "Runs tests that need PostgreSQL and Kafka."
    group = "verification"
    testClassesDirs = integrationTest.output.classesDirs
    classpath = integrationTest.runtimeClasspath
    shouldRunAfter(tasks.named("test"))
    useJUnitPlatform()
    // Forward the optional external database so tests can run without Docker.
    environment("TEST_DATABASE_URL", System.getenv("TEST_DATABASE_URL") ?: "")
}

tasks.named("check") { dependsOn("integrationTest") }
