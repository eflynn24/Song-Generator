import React from "react";

export function SongLibrary({ songs, error, onSelect, onDelete }) {
  return (
    <section className="library">
      <div className="library-heading">
        <div>
          <p className="eyebrow">Your saved songs</p>
          <h2>Song library</h2>
        </div>
        <span>{songs.length}</span>
      </div>
      {error && <p className="inline-error">{error}</p>}
      {songs.length === 0 ? (
        <p className="library-empty">Your generated songs will appear here.</p>
      ) : (
        <ul>
          {songs.map((song) => (
            <li key={song.id}>
              <button
                className="library-song"
                type="button"
                onClick={() => onSelect(song)}
              >
                <strong>{song.title || song.request.prompt}</strong>
                <span>
                  {song.status}
                  {" · "}
                  {new Date(song.created_at).toLocaleString()}
                </span>
              </button>
              <button
                className="delete-button"
                type="button"
                aria-label={`Delete ${song.title || "song"}`}
                onClick={() => onDelete(song.id)}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
