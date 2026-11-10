package dev.benchline.benchmark.consumer;

/** The payload cannot be read. Retrying will not help, so it goes straight to the DLQ. */
public class MalformedEventException extends RuntimeException {

    public MalformedEventException(String message, Throwable cause) {
        super(message, cause);
    }
}
