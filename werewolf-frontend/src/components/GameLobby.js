// src/components/GameLobby.js
import React from 'react';

export const GameLobby = ({ players, onSelectPlayer, onStartGame }) => (
  <div className="bg-white p-4 rounded-lg shadow mb-4">
    <h2 className="text-xl font-semibold mb-4">Game Lobby</h2>
    <div className="grid grid-cols-3 gap-4 mb-4">
      {players.map((player) => (
        <button
          key={player.player_id}
          onClick={() => onSelectPlayer(player.player_id)}
          className="bg-gray-100 p-2 rounded hover:bg-gray-200"
        >
          {player.name}
        </button>
      ))}
    </div>
    <button
      onClick={onStartGame}
      className="bg-green-500 text-white px-4 py-2 rounded"
    >
      Start Game
    </button>
  </div>
);