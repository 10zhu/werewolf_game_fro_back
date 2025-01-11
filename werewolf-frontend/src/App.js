// src/App.js
import React, { useState, useEffect } from 'react';
import { GameLobby } from './components/GameLobby';
import { GameBoard } from './components/GameBoard';
import { PlayerActions } from './components/PlayerActions';
import { GameStatus } from './components/GameStatus';

const App = () => {
  const [gameSession, setGameSession] = useState(null);
  const [players, setPlayers] = useState([]);
  const [currentPlayer, setCurrentPlayer] = useState(null);
  const [gamePhase, setGamePhase] = useState('SETUP');
  const [socket, setSocket] = useState(null);

  useEffect(() => {
    if (gameSession) {
      const ws = new WebSocket(`ws://localhost:8000/ws/game/${gameSession}/`);
      
      ws.onmessage = (event) => {
        console.log("receiving message" + event)
        const data = JSON.parse(event.data);
        handleGameUpdate(data);
      };
      // TODO: send message to backend via websocket

      setSocket(ws);

      return () => ws.close();
    }
  }, [gameSession]);

  const handleGameUpdate = (data) => {
    if (data.type === 'phase_update') {
      setGamePhase(data.phase);
    } else if (data.type === 'player_update') {
      setPlayers(data.players);
    }
  };

  const createGame = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/games/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: Date.now().toString() }),
      });
      const data = await response.json();
      setGameSession(data.session_id);
    } catch (error) {
      console.error('Error creating game:', error);
    }
  };

  const startGame = async () => {
    try {
      const resp = await fetch(`http://localhost:8000/api/games/${gameSession}/start_game/`, {
        method: 'POST',

      });
      const data = await resp.json();
        console.log(data);
        handleGameUpdate(data);
    } catch (error) {
      console.error('Error starting game:', error);
    }
  };

  const submitAction = async (action, targetId) => {
    try {
      await fetch(`http://localhost:8000/api/games/${gameSession}/submit_action/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          player_id: currentPlayer,
          action,
          target_id: targetId,
        }),
      });
    } catch (error) {
      console.error('Error submitting action:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Werewolf Game</h1>
        
        {!gameSession ? (
          <button
            onClick={createGame}
            className="bg-blue-500 text-white px-4 py-2 rounded"
          >
            Create New Game
          </button>
        ) : (
          <>
            <GameStatus
              gameSession={gameSession}
              gamePhase={gamePhase}
              currentPlayer={currentPlayer}
            />
            
            {gamePhase === 'SETUP' && (
              <GameLobby
                players={players}
                onSelectPlayer={setCurrentPlayer}
                onStartGame={startGame}
              />
            )}
            
            {gamePhase !== 'SETUP' && (
              <>
                <GameBoard
                  players={players}
                  currentPlayer={currentPlayer}
                  gamePhase={gamePhase}
                />
                <PlayerActions
                  gamePhase={gamePhase}
                  onSubmitAction={submitAction}
                  players={players}
                />
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default App;