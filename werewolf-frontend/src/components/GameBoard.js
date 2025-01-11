// src/components/GameBoard.js
import React from 'react';

export const GameBoard = ({ players, currentPlayer, gamePhase }) => (
  <div className="bg-white p-4 rounded-lg shadow mb-4">
    <h2 className="text-xl font-semibold mb-4">Players</h2>
    <div className="grid grid-cols-3 gap-4">
      {players.map((player) => (
        <div
          key={player.player_id}
          className={`p-4 rounded ${
            player.player_id === currentPlayer
              ? 'bg-blue-100'
              : 'bg-gray-100'
          }`}
        >
          <p className="font-semibold">{player.name}</p>
          <p>Status: {player.status}</p>
          {player.role && <p>Role: {player.role}</p>}
        </div>
      ))}
    </div>
  </div>
);