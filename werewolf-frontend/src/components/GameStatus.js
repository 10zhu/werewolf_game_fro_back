// src/components/GameStatus.js
import React from 'react';

export const GameStatus = ({ gameSession, gamePhase, currentPlayer }) => (
  <div className="bg-white p-4 rounded-lg shadow mb-4">
    <h2 className="text-xl font-semibold mb-2">Game Status</h2>
    <p>Session ID: {gameSession}</p>
    <p>Phase: {gamePhase}</p>
    <p>Your Position: {currentPlayer ? `Position ${parseInt(currentPlayer.replace('p', '')) + 1}` : 'Not selected'}</p>
  </div>
);