import React, { useState } from "react";
import Autocomplete from "./Autocomplete";

interface Player {
  player_id: number;
  web_name: string;
}

interface OptimalTransfer {
  outgoing_player: Player;
  incoming_player: {
    player_id: number;
    web_name: string;
    position: string;
    cost: number; // Stored in pence
    points: number;
  };
  improvement: number;
}

interface BestTeam {
  players: Player[];
}

function App() {
  const [team, setTeam] = useState<Player[]>([]);
  const [remainingBudget, setRemainingBudget] = useState<string>("");
  const [optimalTransfer, setOptimalTransfer] = useState<OptimalTransfer | null>(null);
  const [bestTeam, setBestTeam] = useState<BestTeam | null>(null);

  const handleAddPlayer = (player: Player) => {
    if (team.some((p) => p.player_id === player.player_id)) {
      alert("Player is already in the team!");
      return;
    }
    setTeam((prevTeam) => [...prevTeam, player]);
  };

  const handleRemovePlayer = (playerId: number) => {
    setTeam((prevTeam) => prevTeam.filter((p) => p.player_id !== playerId));
  };

  const handleBudgetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setRemainingBudget(e.target.value);
  };

  const handleSubmit = async () => {
    if (team.length === 0) {
      alert("Please enter your exact team of 15 players.");
      return;
    }
    if (!remainingBudget || isNaN(Number(remainingBudget))) {
      alert("Please enter a valid remaining budget.");
      return;
    }

    try {
      const response = await fetch("http://34.55.194.187/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_team: team,
          remaining_budget: parseFloat(remainingBudget),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      if (data.success) {
        setOptimalTransfer({
          outgoing_player: data.optimal_transfer.outgoing_player,
          incoming_player: {
            player_id: data.optimal_transfer.incoming_player.player_id,
            web_name: data.optimal_transfer.incoming_player.web_name,
            position: data.optimal_transfer.incoming_player.position,
            cost: Number(data.optimal_transfer.incoming_player.cost),
            points: Number(data.optimal_transfer.incoming_player.points),
          },
          improvement: Number(data.optimal_transfer.improvement),
        });
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (error) {
      console.error("Error fetching optimal transfer:", error);
      alert("An error occurred while fetching the optimal transfer.");
    }
  };

  const handleBestTeamRequest = async () => {
    try {
      const response = await fetch("http://34.55.194.187/best_team");
  
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
  
      const data = await response.json();
  
      if (data.success && data.best_team && data.best_team.players) {
        setBestTeam({ players: data.best_team.players });
      } else {
        console.warn("Unexpected data structure:", data);
        alert("Received unexpected data. Please contact support.");
      }
    } catch (error) {
      console.error("Error fetching the best team:");
      alert("An error occurred while fetching the best team. Please try again later.");
    }
  };
  

  return (
    <div style={{ margin: "2rem" }}>
      <h1>FPL Threat Predictor</h1>
      <div>
        <h3>Input Your Current Team</h3>
        <Autocomplete
          placeholder="Search for a player"
          onPlayerSelect={handleAddPlayer}
        />
      </div>
      <div style={{ marginTop: "1rem" }}>
        <h4>Your Current Team:</h4>
        <ul>
          {team.map((player) => (
            <li key={player.player_id} style={{ marginBottom: "0.5rem" }}>
              {player.web_name}{" "}
              <button
                onClick={() => handleRemovePlayer(player.player_id)}
                style={{
                  marginLeft: "1rem",
                  padding: "0.2rem 0.5rem",
                  color: "white",
                  background: "red",
                  border: "none",
                  borderRadius: "3px",
                  cursor: "pointer",
                  zIndex: 1000,
                }}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      </div>
      <div style={{ marginTop: "1rem" }}>
        <label>
          Remaining Budget (£):{" "}
          <input
            type="number"
            value={remainingBudget}
            onChange={handleBudgetChange}
            placeholder="Enter your remaining budget"
            style={{
              padding: "0.5rem",
              border: "1px solid #ccc",
              borderRadius: "4px",
              width: "200px",
            }}
          />
        </label>
      </div>
      <button
        onClick={handleSubmit}
        style={{
          marginTop: "1rem",
          padding: "0.7rem 2rem",
          background: "green",
          color: "white",
          border: "none",
          borderRadius: "5px",
          cursor: "pointer",
        }}
      >
        Predict Threat
      </button>
      <button
        onClick={handleBestTeamRequest}
        style={{
          marginTop: "1rem",
          padding: "0.7rem 2rem",
          background: "blue",
          color: "white",
          border: "none",
          borderRadius: "5px",
          cursor: "pointer",
        }}
      >
        Get Best Team
      </button>
      {optimalTransfer && (
        <div style={{ marginTop: "2rem" }}>
          <h3>Optimal Transfer:</h3>
          <p>
            <strong>Outgoing Player:</strong> {optimalTransfer.outgoing_player.web_name}
          </p>
          <p>
            <strong>Incoming Player:</strong> {optimalTransfer.incoming_player.position}{" "}
            {optimalTransfer.incoming_player.web_name} costing £
            {(optimalTransfer.incoming_player.cost / 10).toFixed(2)} with{" "}
            {optimalTransfer.incoming_player.points.toFixed(2)} points.
          </p>
          <p>
            <strong>Improvement:</strong>{" "}
            {optimalTransfer.improvement.toFixed(2)} points
          </p>
        </div>
      )}
      {bestTeam && (
        <div style={{ marginTop: "2rem" }}>
          <h3>Best Team:</h3>
          <ul>
            {bestTeam.players.map((player) => (
              <li key={player.player_id}>{player.web_name}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default App;
