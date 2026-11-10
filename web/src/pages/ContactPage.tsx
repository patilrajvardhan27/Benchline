import { type SyntheticEvent, useId, useState } from "react";
import { z } from "zod";
import { config } from "../shared/config";
import { PageShell } from "../shared/ui/PageShell";

const schema = z.object({
  email: z.email("Enter a valid email address."),
  topic: z.enum(["question", "bug", "security", "accessibility", "legal"]),
  message: z.string().trim().min(10, "Write at least 10 characters.").max(2000, "Keep it under 2000 characters."),
});

const TOPICS: Record<z.infer<typeof schema>["topic"], string> = {
  question: "A question",
  bug: "A bug",
  security: "A security issue",
  accessibility: "An accessibility problem",
  legal: "A legal or privacy request",
};

const text = (value: FormDataEntryValue | null) => (typeof value === "string" ? value : "");

type Errors = Partial<Record<"email" | "message", string>>;

const openMailClient = (url: string) => { window.location.href = url; };

/** `onCompose` is injectable so tests can observe the mailto link without navigating. */
export function ContactPage({ onCompose = openMailClient }: { onCompose?: (url: string) => void }) {
  const ids = { email: useId(), topic: useId(), message: useId() };
  const [errors, setErrors] = useState<Errors>({});

  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const parsed = schema.safeParse({
      email: text(form.get("email")),
      topic: text(form.get("topic")),
      message: text(form.get("message")),
    });
    if (!parsed.success) {
      const next: Errors = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0];
        if ((key === "email" || key === "message") && !next[key]) next[key] = issue.message;
      }
      setErrors(next);
      return;
    }
    setErrors({});
    const { email, topic, message } = parsed.data;
    const subject = `Benchline: ${TOPICS[topic]}`;
    const body = `${message}\n\nReply to: ${email}`;
    onCompose(`mailto:${config.contactEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`);
  };

  return (
    <PageShell title="Contact" description="Questions, bug reports, accessibility problems and security reports.">
      <div className="grid-2">
        <form onSubmit={submit} noValidate className="panel" aria-label="Contact form">
          <div className="field">
            <label htmlFor={ids.topic}>What is this about?</label>
            <select id={ids.topic} name="topic" defaultValue="question">
              {Object.entries(TOPICS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor={ids.email}>Your email</label>
            <input id={ids.email} name="email" type="email" autoComplete="email"
              aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? `${ids.email}-e` : undefined} />
            {errors.email && <span id={`${ids.email}-e`} className="error" role="alert">{errors.email}</span>}
          </div>
          <div className="field">
            <label htmlFor={ids.message}>Message</label>
            <textarea id={ids.message} name="message"
              aria-invalid={Boolean(errors.message)} aria-describedby={errors.message ? `${ids.message}-e` : undefined} />
            {errors.message && <span id={`${ids.message}-e`} className="error" role="alert">{errors.message}</span>}
          </div>
          <button type="submit" className="btn">Open in my email app</button>
          <p className="muted" style={{ marginTop: "var(--bl-space-3)" }}>
            This opens a draft in your email app. Nothing is sent to our servers from this page.
          </p>
        </form>
        <section aria-labelledby="direct-h" className="prose">
          <h2 id="direct-h">Email directly</h2>
          <p><a href={`mailto:${config.contactEmail}`}>{config.contactEmail}</a></p>
          <h2>Reporting a security problem</h2>
          <p>
            Please email with the subject "Security" and enough detail to reproduce it. Do not access data
            that is not yours or disrupt the service while testing. We will acknowledge within five working
            days and credit you if you want.
          </p>
        </section>
      </div>
    </PageShell>
  );
}
