package dev.benchline.common.errors;

import jakarta.servlet.http.HttpServletRequest;
import java.net.URI;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

/**
 * Turns every failure into RFC 9457 problem+json. Unexpected exceptions are
 * logged with their stack trace on the server and reach the caller only as a
 * generic 500 with a trace id, so internals never leak.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);
    private static final String TYPE_BASE = "https://benchline.dev/problems/";

    @ExceptionHandler(ApiException.class)
    ResponseEntity<ProblemDetail> handleApi(ApiException ex, HttpServletRequest req) {
        return problem(ex.status(), ex.getMessage(), req, List.of());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<ProblemDetail> handleValidation(MethodArgumentNotValidException ex, HttpServletRequest req) {
        List<FieldIssue> issues = ex.getBindingResult().getFieldErrors().stream()
                .map(e -> new FieldIssue(e.getField(), String.valueOf(e.getDefaultMessage())))
                .toList();
        return problem(HttpStatus.BAD_REQUEST, "The request body failed validation", req, issues);
    }

    @ExceptionHandler({HttpMessageNotReadableException.class, MethodArgumentTypeMismatchException.class})
    ResponseEntity<ProblemDetail> handleUnreadable(Exception ex, HttpServletRequest req) {
        return problem(HttpStatus.BAD_REQUEST, "The request could not be read", req, List.of());
    }

    @ExceptionHandler(NoResourceFoundException.class)
    ResponseEntity<ProblemDetail> handleNoResource(NoResourceFoundException ex, HttpServletRequest req) {
        return problem(HttpStatus.NOT_FOUND, "No such resource", req, List.of());
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<ProblemDetail> handleUnexpected(Exception ex, HttpServletRequest req) {
        log.error("Unhandled error on {} {}", req.getMethod(), req.getRequestURI(), ex);
        return problem(HttpStatus.INTERNAL_SERVER_ERROR, "Something went wrong on our side", req, List.of());
    }

    private ResponseEntity<ProblemDetail> problem(
            HttpStatus status, String detail, HttpServletRequest req, List<FieldIssue> issues) {
        ProblemDetail body = ProblemDetail.forStatusAndDetail(status, detail);
        body.setType(URI.create(TYPE_BASE + status.name().toLowerCase().replace('_', '-')));
        body.setTitle(status.getReasonPhrase());
        body.setInstance(URI.create(req.getRequestURI()));
        String traceId = MDC.get("trace_id");
        if (traceId != null) {
            body.setProperty("traceId", traceId);
        }
        if (!issues.isEmpty()) {
            body.setProperty("errors", issues);
        }
        return ResponseEntity.status(status).contentType(MediaType.APPLICATION_PROBLEM_JSON).body(body);
    }

    /** One rejected field in a validation problem. */
    public record FieldIssue(String field, String message) {}
}
