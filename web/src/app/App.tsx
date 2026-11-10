import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "../shared/api/auth";
import { ErrorBoundary } from "./ErrorBoundary";
import { createQueryClient } from "./queryClient";
import { AppRoutes } from "./routes";

export function App() {
  const [client] = useState(createQueryClient);
  return (
    <ErrorBoundary>
      <QueryClientProvider client={client}>
        <AuthProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
