package dev.benchline.pricing;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication(scanBasePackages = "dev.benchline")
@EnableScheduling
public class PricingApiApplication {

    public static void main(String[] args) {
        SpringApplication.run(PricingApiApplication.class, args);
    }
}
