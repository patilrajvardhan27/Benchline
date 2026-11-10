package dev.benchline.benchmark;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = "dev.benchline")
public class BenchmarkWorkerApplication {

    public static void main(String[] args) {
        SpringApplication.run(BenchmarkWorkerApplication.class, args);
    }
}
