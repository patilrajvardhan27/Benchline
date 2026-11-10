package dev.benchline.testsupport;

import static org.junit.jupiter.api.Assumptions.assumeTrue;

import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.DockerClientFactory;
import org.testcontainers.containers.PostgreSQLContainer;

/**
 * Gives each integration test a migrated PostgreSQL. It uses Testcontainers
 * unless TEST_DATABASE_URL points at a throwaway database (user and password
 * come from TEST_DATABASE_USER and TEST_DATABASE_PASSWORD), which lets the
 * suite run on machines without Docker. Tests are skipped if neither exists.
 */
public abstract class PostgresTestBase {

    private static String url;
    private static String user;
    private static String password;
    private static PostgreSQLContainer<?> container;

    @BeforeAll
    static void startDatabase() {
        if (url != null) {
            return;
        }
        String external = System.getenv("TEST_DATABASE_URL");
        if (external != null && !external.isBlank()) {
            url = external;
            user = System.getenv().getOrDefault("TEST_DATABASE_USER", "postgres");
            password = System.getenv().getOrDefault("TEST_DATABASE_PASSWORD", "");
        } else {
            assumeTrue(DockerClientFactory.instance().isDockerAvailable(), "Docker or TEST_DATABASE_URL is required");
            container = new PostgreSQLContainer<>("postgres:16-alpine");
            container.start();
            url = container.getJdbcUrl();
            user = container.getUsername();
            password = container.getPassword();
        }
        Flyway.configure()
                .dataSource(url, user, password)
                .locations("classpath:migrations")
                .load()
                .migrate();
    }

    @DynamicPropertySource
    static void datasource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", () -> url);
        registry.add("spring.datasource.username", () -> user);
        registry.add("spring.datasource.password", () -> password);
    }

    @BeforeEach
    void cleanTables() {
        DriverManagerDataSource ds = new DriverManagerDataSource(url, user, password);
        new JdbcTemplate(ds).execute("""
                TRUNCATE insights.price_anomaly, benchmark.benchmark_snapshot, benchmark.processed_event,
                         member.purchase_line, member.facility, pricing.outbox_event, pricing.price_point,
                         catalog.item, catalog.item_group RESTART IDENTITY CASCADE
                """);
    }
}
