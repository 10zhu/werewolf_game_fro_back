// src/components/PlayerActions.js
import React, { useState } from 'react';

export const PlayerActions = ({ gamePhase, onSubmitAction, players }) => {
  const [selectedAction, setSelectedAction] = useState('');
  const [targetPlayer, setTargetPlayer] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (selectedAction && targetPlayer) {
      onSubmitAction(selectedAction, targetPlayer);
      setSelectedAction('');
      setTargetPlayer('');
    }
  };

  const actions = {
    NIGHT: ['kill', 'check', 'heal', 'poison'],
    DAY: ['vote'],
    POLICEMAN_SELECTION: ['vote_policeman'],
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4">Actions</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block mb-2">Action:</label>
          <select
            value={selectedAction}
            onChange={(e) => setSelectedAction(e.target.value)}
            className="w-full p-2 border rounded"
          >
            <option value="">Select action</option>
            {actions[gamePhase]?.map((action) => (
              <option key={action} value={action}>
                {action}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block mb-2">Target:</label>
          <select
            value={targetPlayer}
            onChange={(e) => setTargetPlayer(e.target.value)}
            className="w-full p-2 border rounded"
          >
            <option value="">Select target</option>
            {players.map((player) => (
              <option key={player.player_id} value={player.player_id}>
                {player.name}
              </option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          className="bg-blue-500 text-white px-4 py-2 rounded w-full"
          disabled={!selectedAction || !targetPlayer}
        >
          Submit Action
        </button>
      </form>
    </div>
  );
};