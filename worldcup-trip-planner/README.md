k# World Cup 2026 Fan Trip Planner

## Live Demo

https://worldcup-trip-planner-ygtajujrxa-uc.a.run.app

## Problem

Planning a World Cup trip is difficult because fans need to coordinate matches, host cities, flights, hotels, visa requirements, travel routes, and budget feasibility across a multi-city tournament.

For the 2026 FIFA World Cup, this becomes even harder because the tournament is spread across the United States, Canada, and Mexico. Fans may want to follow a specific team, attend the final, or understand whether their budget is realistic before committing to travel.

## Solution

World Cup 2026 Fan Trip Planner is an AI-powered travel planning assistant that turns a fan's travel intent into a structured itinerary.

Users can choose a team or the World Cup Final, enter their departure airport, citizenship, and budget, and receive a practical matchday travel plan. The app generates match stops, host cities, stadiums, hotel nights, estimated flight and lodging costs, visa guidance, and a budget verdict.

The result is a clear travel-planning experience that helps fans understand where they need to go, how much the trip may cost, and whether their plan is realistic.

## Features

- Follow a selected national team through the World Cup group stage
- Plan a trip to the World Cup Final
- Enter departure airport, citizenship, and budget
- Generate structured matchday itineraries
- Estimate flight and lodging costs
- Check whether the trip is within budget
- Provide visa and travel requirement guidance
- Handle low-budget edge cases
- Visualize host cities and routes on a map
- Deployed publicly on Google Cloud Run

## Architecture

```text
User
  ↓
Frontend HTML/CSS/JavaScript
  ↓
Flask API Server
  ↓
Google ADK / Gemini Agent
  ↓
MongoDB Atlas + Custom Travel Tools
  ↓
Structured Itinerary Response
  ↓
Frontend renders itinerary, budget verdict, and map route
