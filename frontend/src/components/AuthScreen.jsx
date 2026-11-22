import React from "react";

export function AuthScreen({
  mode,
  setMode,
  credentials,
  setCredentials,
  onSubmit,
  onGuest,
  busy,
  error,
}) {
  const registering = mode === "register";
  return (
    <main className="auth-page">
      <section className="auth-card">
        <p className="eyebrow">Studio / Local</p>
        <h1>Song Generator</h1>
        <p className="auth-intro">
          {registering
            ? "Create an account to keep your song library."
            : "Sign in, or start a temporary guest session."}
        </p>
        <form onSubmit={onSubmit}>
          <label>
            Username
            <input
              autoComplete="username"
              minLength="3"
              maxLength="32"
              value={credentials.username}
              onChange={(event) =>
                setCredentials((current) => ({
                  ...current,
                  username: event.target.value,
                }))
              }
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              autoComplete={registering ? "new-password" : "current-password"}
              minLength={registering ? 12 : 1}
              maxLength="256"
              value={credentials.password}
              onChange={(event) =>
                setCredentials((current) => ({
                  ...current,
                  password: event.target.value,
                }))
              }
              required
            />
          </label>
          {error && <p className="inline-error">{error}</p>}
          <button type="submit" disabled={busy}>
            {busy
              ? "Please wait..."
              : registering
                ? "Create account"
                : "Sign in"}
          </button>
        </form>
        {!registering && (
          <button
            className="guest-button"
            type="button"
            onClick={onGuest}
            disabled={busy}
          >
            Continue as guest — no password
          </button>
        )}
        <button
          className="text-button"
          type="button"
          onClick={() => setMode(registering ? "login" : "register")}
        >
          {registering
            ? "Already have an account? Sign in"
            : "New here? Create an account"}
        </button>
      </section>
    </main>
  );
}

export function PasswordScreen({
  values,
  setValues,
  onSubmit,
  busy,
  error,
  onSignOut,
  required,
  onCancel,
}) {
  return (
    <main className="auth-page">
      <section className="auth-card">
        <p className="eyebrow">Secure your account</p>
        <h1>Set a new password</h1>
        <p className="auth-intro">
          {required
            ? "Change the one-time setup password before opening your song library."
            : "Choose a new password for your account."}
        </p>
        <form onSubmit={onSubmit}>
          {[
            ["current_password", "Temporary password", "current-password"],
            ["new_password", "New password (at least 12 characters)", "new-password"],
            ["confirmation", "Confirm new password", "new-password"],
          ].map(([name, label, autocomplete]) => (
            <label key={name}>
              {label}
              <input
                type="password"
                autoComplete={autocomplete}
                minLength={name === "current_password" ? 1 : 12}
                value={values[name]}
                onChange={(event) =>
                  setValues((current) => ({
                    ...current,
                    [name]: event.target.value,
                  }))
                }
                required
              />
            </label>
          ))}
          {error && <p className="inline-error">{error}</p>}
          <button type="submit" disabled={busy}>
            {busy ? "Saving..." : "Change password"}
          </button>
        </form>
        <div className="auth-actions">
          {!required && (
            <button className="text-button" type="button" onClick={onCancel}>
              Cancel
            </button>
          )}
          <button className="text-button" type="button" onClick={onSignOut}>
            Sign out
          </button>
        </div>
      </section>
    </main>
  );
}
