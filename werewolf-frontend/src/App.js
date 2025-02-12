// src/App.js
import React, { useState, useEffect } from 'react';
import { GameLobby } from './components/GameLobby';
import { GameBoard } from './components/GameBoard';
import { PlayerActions } from './components/PlayerActions';
import { GameStatus } from './components/GameStatus';
import { RoomList } from './components/RoomList';

const App = () => {
  const [gameSession, setGameSession] = useState(null);
  const [players, setPlayers] = useState([]);
  const [currentPlayer, setCurrentPlayer] = useState(null);
  const [gamePhase, setGamePhase] = useState('SETUP');
  const [socket, setSocket] = useState(null);
  const [showRoomList, setShowRoomList] = useState(true);


  useEffect(() => {
    if (gameSession) {
      const ws = new WebSocket(`ws://localhost:8000/ws/game/${gameSession}/`);

      ws.onmessage = (event) => {
        console.log("Receiving message:", event.data);
        const data = JSON.parse(event.data);

        switch (data.type) {
          case 'game_state':
            console.log("Game state update:", data);
            setGamePhase(data.phase);
            setPlayers(data.players || []);
            break;

          case 'phase_update':
            setGamePhase(data.phase);
            break;

          case 'player_update':
            setPlayers(data.players);
            break;

          default:
            console.log('Unknown message type:', data.type);
        }
      };

      setSocket(ws);

      return () => ws.close();
    }
  }, [gameSession]);

  const handleGameUpdate = (data) => {
  console.log("Handling game update, received data:", data); // Debug log
  if (data.type === 'game_state') {
    if (data.players && Array.isArray(data.players)) {
      console.log("Setting players:", data.players);
      setPlayers(data.players);
      setGamePhase(data.phase);
    } else {
      console.warn("Invalid players data received:", data.players);
    }
  } else if (data.type === 'phase_update') {
    setGamePhase(data.phase);
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
      setShowRoomList(false);
    } catch (error) {
      console.error('Error creating game:', error);
    }
  };

const handleSelectRoom = (sessionId) => {
    setGameSession(sessionId);
    setShowRoomList(false);
  };

  const leaveRoom = () => {
    if (socket) {
      socket.close();
    }
    setGameSession(null);
    setPlayers([]);
    setCurrentPlayer(null);
    setGamePhase('SETUP');
    setShowRoomList(true);
  };


  const startGame = async () => {
  try {
    if (!currentPlayer && players.length > 0) {
      setCurrentPlayer(players[0].player_id);
    }

    const resp = await fetch(`http://localhost:8000/api/games/${gameSession}/start_game/`, {
      method: 'POST',
    });
    const data = await resp.json();
    console.log("Start game response received:", data); // Debug log to see the response
    handleGameUpdate(data);
  } catch (error) {
    console.error('Error starting game:', error);
  }
};
//    const startGame = () => {
//      if (socket && socket.readyState === WebSocket.OPEN) {
//        socket.send(JSON.stringify({
//          type: 'start_game'
//        }));
//      }
//    };

  const submitAction = async (action, targetId) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: 'player_action',
        player_id: currentPlayer,
        action,
        target_id: targetId
      }));
    } else {
      console.error('WebSocket is not connected');
    }
  };

  // Add this to help with debugging
  console.log("Current state:", {
    gamePhase,
    currentPlayer,
    playersCount: players.length,
    players
  });

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Werewolf Game</h1>
          {gameSession && (
            <button
              onClick={leaveRoom}
              className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
            >
              Leave Room
            </button>
          )}
        </div>

        {showRoomList ? (
          <div className="space-y-4">
            <RoomList onSelectRoom={handleSelectRoom} />
            <div className="text-center">
              <button
                onClick={createGame}
                className="bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 transition-colors"
              >
                Create New Game
              </button>
            </div>
          </div>
        ) : (
          <>
            <GameStatus
              gameSession={gameSession}
              gamePhase={gamePhase}
              currentPlayer={currentPlayer}
            />

            {gamePhase === 'SETUP' ? (
              <GameLobby
                players={players}
                onSelectPlayer={setCurrentPlayer}
                onStartGame={startGame}
                currentPlayer={currentPlayer}
              />
            ) : (
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
                  playerRole={players.find(p => p.player_id === currentPlayer)?.role}
                  currentPlayer={currentPlayer}
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

//import React, { useState, useEffect } from 'react';
//import { GameLobby } from './components/GameLobby';
//import { GameBoard } from './components/GameBoard';
//import { PlayerActions } from './components/PlayerActions';
//import { GameStatus } from './components/GameStatus';
//
//const App = () => {
//  const [gameSession, setGameSession] = useState(null);
//  const [players, setPlayers] = useState([]);
//  const [currentPlayer, setCurrentPlayer] = useState(null);
//  const [gamePhase, setGamePhase] = useState('SETUP');
//  const [socket, setSocket] = useState(null);
//
//  useEffect(() => {
//    if (gameSession) {
//      const ws = new WebSocket(`ws://localhost:8000/ws/game/${gameSession}/`);
//
//      ws.onmessage = (event) => {
//        console.log("receiving message" + event)
//        const data = JSON.parse(event.data);
////        handleGameUpdate(data);
//     switch (data.type) {
//            case 'game_state':
//              // Update the entire game state
//              setGamePhase(data.phase);
//              setPlayers(data.players);
//              // If no player is selected and we have players, select the first one
//                if (!currentPlayer && data.players?.length > 0) {
//                  setCurrentPlayer(data.players[0].player_id);
//                }
//              break;
//
//            case 'phase_update':
//              setGamePhase(data.phase);
//              break;
//
//            case 'player_update':
//              setPlayers(data.players);
//              break;
//
//            case 'error':
//              console.error('Game error:', data.message);
//              break;
//
//            default:
//              console.log('Unknown message type:', data.type);
//          }
//      };
//      // TODO: send message to backend via websocket
//      // Add function to send messages via WebSocket
//        const sendWebSocketMessage = (type, payload) => {
//          if (ws.readyState === WebSocket.OPEN) {
//            ws.send(JSON.stringify({
//              type,
//              ...payload
//            }));
//          }
//        };
//
//        // Update submitAction to use WebSocket
//        const submitActionViaWebSocket = (action, targetId) => {
//          sendWebSocketMessage('player_action', {
//            player_id: currentPlayer,
//            action,
//            target_id: targetId
//          });
//        };
//
//      setSocket(ws);
//
//      return () => ws.close();
////        return () => {
////          if (ws.readyState === WebSocket.OPEN) {
////            ws.close();
////          }
////        };
//    }
//  }, [gameSession, currentPlayer]);
//
//  const handleGameUpdate = (data) => {
//    if (data.type === 'phase_update') {
//      setGamePhase(data.phase);
//    } else if (data.type === 'player_update') {
//      setPlayers(data.players);
//    }
//  };
//
//  const createGame = async () => {
//    try {
//      const response = await fetch('http://localhost:8000/api/games/', {
//        method: 'POST',
//        headers: {
//          'Content-Type': 'application/json',
//        },
//        body: JSON.stringify({ session_id: Date.now().toString() }),
//      });
//      const data = await response.json();
//      setGameSession(data.session_id);
//    } catch (error) {
//      console.error('Error creating game:', error);
//    }
//  };
//
//  const startGame = async () => {
//    try {
//        if (!currentPlayer) {
//          console.error('No player selected');
//          return;
//        }
//        // Ensure a player is selected before starting
//          if (!currentPlayer && players.length > 0) {
//            setCurrentPlayer(players[0].player_id);
//          }
//      const resp = await fetch(`http://localhost:8000/api/games/${gameSession}/start_game/`, {
//        method: 'POST',
//
//      });
//      const data = await resp.json();
//        console.log("Start game response:", data);
//        handleGameUpdate(data);
//    } catch (error) {
//      console.error('Error starting game:', error);
//    }
//  };
//
//  const submitAction = async (action, targetId) => {
//    if (socket && socket.readyState === WebSocket.OPEN) {
//    socket.send(JSON.stringify({
//      type: 'player_action',
//      player_id: currentPlayer,
//      action,
//      target_id: targetId
//    }));
//  } else {
//    console.error('WebSocket is not connected');
//  }
//
////    try {
////      await fetch(`http://localhost:8000/api/games/${gameSession}/submit_action/`, {
////        method: 'POST',
////        headers: {
////          'Content-Type': 'application/json',
////        },
////        body: JSON.stringify({
////          player_id: currentPlayer,
////          action,
////          target_id: targetId,
////        }),
////      });
////    } catch (error) {
////      console.error('Error submitting action:', error);
////    }
//
//  };
//
//  // Update the PlayerActions component to show appropriate actions based on player role
//      const getCurrentPlayerRole = () => {
//        return players.find(p => p.player_id === currentPlayer)?.role;
//      };
//
//  return (
//    <div className="min-h-screen bg-gray-100 p-8">
//      <div className="max-w-4xl mx-auto">
//        <h1 className="text-3xl font-bold mb-8">Werewolf Game</h1>
//
//        {!gameSession ? (
//          <button
//            onClick={createGame}
//            className="bg-blue-500 text-white px-4 py-2 rounded"
//          >
//            Create New Game
//          </button>
//        ) : (
//          <>
//            <GameStatus
//              gameSession={gameSession}
//              gamePhase={gamePhase}
//              currentPlayer={currentPlayer}
//            />
//
//            {gamePhase === 'SETUP' && (
//              <GameLobby
//                players={players}
//                onSelectPlayer={setCurrentPlayer}
//                onStartGame={startGame}
//                currentPlayer={currentPlayer}
//              />
//            )}
//
//            {gamePhase !== 'SETUP' && currentPlayer &&(
//              <>
//                <GameBoard
//                  players={players}
//                  currentPlayer={currentPlayer}
//                  gamePhase={gamePhase}
//                />
//                <PlayerActions
//                  gamePhase={gamePhase}
//                  onSubmitAction={submitAction}
//                  players={players}
//                  playerRole={getCurrentPlayerRole()}
//                />
//              </>
//            )}
//          </>
//        )}
//      </div>
//    </div>
//  );
//};
//
//export default App;