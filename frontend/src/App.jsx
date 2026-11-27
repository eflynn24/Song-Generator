import React, { useEffect, useState } from "react";
import { apiRequest } from "./api";
import { AuthScreen, PasswordScreen } from "./components/AuthScreen";
import { SongForm } from "./components/SongForm";
import { SongLibrary } from "./components/SongLibrary";
import { SongResult } from "./components/SongResult";

const EMPTY_PASSWORD_CHANGE = {
  current_password: "",
  new_password: "",
  confirmation: "",
};

export default function App() {
  const [account, setAccount] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authMode, setAuthMode] = useState("login");
  const [authError, setAuthError] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [passwordMode, setPasswordMode] = useState(false);
  const [credentials, setCredentials] = useState({ username: "user", password: "" });
  const [passwordChange, setPasswordChange] = useState(EMPTY_PASSWORD_CHANGE);
  const [job, setJob] = useState(null);
  const [library, setLibrary] = useState([]);
  const [libraryError, setLibraryError] = useState("");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    let active = true;
    apiRequest("/auth/me")
      .then((result) => active && setAccount(result))
      .catch((error) => {
        if (active && error.status !== 401) setAuthError(error.message);
      })
      .finally(() => active && setAuthLoading(false));
    fetch("/api/health")
      .then((response) => response.json())
      .then((result) => active && setHealth(result))
      .catch(() => active && setHealth({ status: "error" }));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!account?.is_guest) return undefined;
    const timer = window.setInterval(() => {
      apiRequest("/auth/ping").catch((error) => {
        if (error.status === 401) setAccount(null);
      });
    }, 5 * 60 * 1000);
    return () => window.clearInterval(timer);
  }, [account]);

  useEffect(() => {
    if (!account || account.must_change_password) {
      setLibrary([]);
      return undefined;
    }
    let active = true;
    const refresh = () => apiRequest("/songs")
      .then((songs) => {
        if (!active) return;
        setLibrary(songs);
        setLibraryError("");
        setJob((current) => songs.find((song) => song.id === current?.id) || current);
      })
      .catch((error) => {
        if (!active) return;
        if (error.status === 401) setAccount(null);
        setLibraryError(error.message);
      });
    refresh();
    const timer = window.setInterval(refresh, 3000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [account]);

  useEffect(() => {
    if (!job || !["queued", "generating"].includes(job.status)) return undefined;
    let active = true;
    const timer = window.setTimeout(async () => {
      try {
        const updated = await apiRequest(`/jobs/${job.id}`);
        if (active) setJob(updated);
      } catch (error) {
        if (!active) return;
        if (error.status === 401) setAccount(null);
        setJob({ ...job, status: "failed", error: error.message });
      }
    }, job.status === "queued" ? 2000 : 1000);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [job]);

  const authenticate = async (event) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    try {
      const result = await apiRequest(`/auth/${authMode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });
      setAccount(result);
      setJob(null);
      setCredentials((current) => ({ ...current, password: "" }));
    } catch (error) {
      setAuthError(error.message);
    } finally {
      setAuthBusy(false);
    }
  };

  const continueAsGuest = async () => {
    setAuthBusy(true);
    setAuthError("");
    try {
      setAccount(await apiRequest("/auth/guest", { method: "POST" }));
      setJob(null);
    } catch (error) {
      setAuthError(error.message);
    } finally {
      setAuthBusy(false);
    }
  };

  const changePassword = async (event) => {
    event.preventDefault();
    setAuthError("");
    if (passwordChange.new_password !== passwordChange.confirmation) {
      setAuthError("The new passwords do not match.");
      return;
    }
    setAuthBusy(true);
    try {
      setAccount(
        await apiRequest("/auth/change-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            current_password: passwordChange.current_password,
            new_password: passwordChange.new_password,
          }),
        }),
      );
      setPasswordChange(EMPTY_PASSWORD_CHANGE);
      setPasswordMode(false);
    } catch (error) {
      setAuthError(error.message);
    } finally {
      setAuthBusy(false);
    }
  };

  const signOut = async () => {
    try {
      await apiRequest("/auth/logout", { method: "POST" });
      setAccount(null);
      setJob(null);
      setLibrary([]);
      setPasswordMode(false);
    } catch (error) {
      setAuthError(error.message);
    }
  };

  const generate = async (form, referenceFile) => {
    let referenceAudioId = null;
    if (referenceFile) {
      const upload = new FormData();
      upload.append("file", referenceFile);
      referenceAudioId = (await apiRequest("/uploads/reference", {
        method: "POST",
        body: upload,
      })).id;
    }
    const newJob = await apiRequest("/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, reference_audio_id: referenceAudioId }),
    });
    setJob(newJob);
    setLibrary((songs) => [newJob, ...songs]);
  };

  const deleteSong = async (songId) => {
    try {
      await apiRequest(`/songs/${songId}`, { method: "DELETE" });
      setLibrary((songs) => songs.filter((song) => song.id !== songId));
      setJob((current) => (current?.id === songId ? null : current));
    } catch (error) {
      setLibraryError(error.message);
    }
  };

  if (authLoading) {
    return (
      <main className="auth-page">
        <div className="empty loading">
          <div className="spinner" />
          <h2>Checking your account</h2>
        </div>
      </main>
    );
  }
  if (!account) {
    return (
      <AuthScreen
        mode={authMode}
        setMode={(mode) => {
          setAuthMode(mode);
          setAuthError("");
        }}
        credentials={credentials}
        setCredentials={setCredentials}
        onSubmit={authenticate}
        onGuest={continueAsGuest}
        busy={authBusy}
        error={authError}
      />
    );
  }
  if (account.must_change_password || passwordMode) {
    return (
      <PasswordScreen
        values={passwordChange}
        setValues={setPasswordChange}
        onSubmit={changePassword}
        busy={authBusy}
        error={authError}
        onSignOut={signOut}
        required={account.must_change_password}
        onCancel={() => {
          setPasswordMode(false);
          setAuthError("");
        }}
      />
    );
  }

  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">Studio / Local</p>
          <h1>Song Generator</h1>
        </div>
        <div className="status">
          <span className={health?.status === "ok" ? "online" : ""} />
          {health?.status === "ok" ? "Backend online" : "Connecting"}
        </div>
        <div className="account-toolbar">
          <span>{account.is_guest ? "Guest session" : account.username}</span>
          {!account.is_guest && (
            <button className="secondary-button" type="button" onClick={() => setPasswordMode(true)}>
              Change password
            </button>
          )}
          <button className="secondary-button" type="button" onClick={signOut}>
            {account.is_guest ? "End guest session" : "Sign out"}
          </button>
        </div>
      </header>
      {account.is_guest && (
        <p className="guest-notice">
          Temporary guest library: it is private to this browser and is erased
          when you end the session or after 20 minutes of inactivity.
        </p>
      )}
      <section className="workspace">
        <div className="studio-column">
          <SongForm
            minimaxAvailable={Boolean(health?.minimax)}
            onGenerate={generate}
          />
          <SongLibrary
            songs={library}
            error={libraryError}
            onSelect={setJob}
            onDelete={deleteSong}
          />
        </div>
        <aside>
          <SongResult job={job} />
        </aside>
      </section>
    </main>
  );
}
