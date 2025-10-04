# Discord Time Tracker Bot

## Overview

This is a Discord bot designed to track user time and attendance across Discord servers. The bot provides comprehensive time tracking functionality with slash commands, automatic milestone notifications, and administrative controls. It features automatic dependency installation, multi-host compatibility, and persistent data storage through JSON files.

## Current Status - ⚠️ AWAITING CONFIGURATION
**Last Updated**: October 02, 2025 (Fresh GitHub Import)

- ✅ **Dependencies Installed**: discord.py 2.6.3, pytz 2025.2
- ⚠️ **Discord Bot Token**: **REQUIRED** - Must be configured as environment secret `DISCORD_BOT_TOKEN`
- ⏸️ **Bot Connected**: Awaiting token configuration
- ⏸️ **Commands Synchronized**: Will sync after bot connects
- ✅ **Workflow Configured**: Ready to run via "Discord Bot" workflow
- ⏸️ **Notification Channels**: Will be accessible after bot connects

### ⚠️ ACTION REQUIRED
**The bot needs a Discord Bot Token to start.** Please add your Discord Bot Token:
1. Click on the "Secrets" tab (Tools → Secrets)
2. Create a new secret with key: `DISCORD_BOT_TOKEN`
3. Paste your Discord Bot Token as the value
4. The bot will automatically restart and connect

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Bot Framework
- **Discord.py Library**: Built on discord.py 2.3.0+ for modern Discord API interaction
- **Slash Commands**: Uses Discord's slash command system for user interactions
- **Event-Driven Architecture**: Handles Discord events like user joins, leaves, and voice channel movements

### Data Storage
- **JSON-Based Persistence**: Uses local JSON files for data storage without external database dependencies
- **File Structure**: 
  - `user_times.json` - Stores user time tracking data and sessions
  - `attendance_data.json` - Stores daily attendance records
  - `config.json` - Bot configuration and settings
- **Auto-Save Mechanism**: Periodic data saving to prevent data loss

### Time Tracking System
- **Session Management**: Tracks start/stop times with pause/resume functionality
- **Milestone Notifications**: Automatically notifies users when reaching time milestones
- **Attendance Tracking**: Daily attendance monitoring with configurable thresholds
- **Administrative Controls**: Admin-only commands for managing user time tracking

### Configuration Management
- **Flexible Token Configuration**: Supports both environment variables and config file token storage
- **Multi-Environment Support**: Compatible with Pterodactyl, Railway, Heroku, and Replit hosting
- **Role-Based Permissions**: Configurable role restrictions for command access
- **Channel Routing**: Specific channels for different notification types

### Auto-Installation System
- **Dependency Detection**: Automatically checks for required packages
- **Multi-Method Installation**: Tries multiple pip installation methods for compatibility
- **Graceful Fallbacks**: Provides clear error messages when auto-installation fails
- **Universal Startup**: Multiple entry points (`bot.py`, `main.py`, `start.py`) for different hosting environments

### Command Architecture
- **Administrative Commands**: Time management, user control, and data cleanup
- **User Commands**: Personal time checking and status commands
- **Notification System**: Automated alerts for milestones, pauses, and attendance
- **Data Export**: Commands for viewing and exporting time tracking data

## Setup Requirements

### Discord Bot Token Configuration (REQUIRED)
**⚠️ IMPORTANT: This bot requires a Discord Bot Token to function.**

To run this bot, you must configure a Discord Bot Token by either:

**Option 1 (Recommended for Replit):** Set as environment variable
1. Go to the Secrets tab in your Replit project
2. Create a new secret with key: `DISCORD_BOT_TOKEN`
3. Set the value to your Discord Bot Token (starts with something like `MTE...`)

**Option 2:** Update config.json
- Edit the `discord_bot_token` field in config.json
- ⚠️ **NOT recommended for shared/public projects** as tokens should be kept secret

### Getting a Discord Bot Token
1. Go to https://discord.com/developers/applications
2. Create a new application or select an existing one
3. Go to the "Bot" section
4. Copy the Bot Token
5. Invite the bot to your Discord server with appropriate permissions

## External Dependencies

### Required Python Packages
- **discord.py (>=2.3.0)**: Primary Discord API library for bot functionality ✅ Installed
- **asyncio**: For asynchronous operations and event handling ✅ Built-in
- **pytz**: Timezone handling and datetime operations ✅ Installed
- **zoneinfo**: Alternative timezone support for newer Python versions ✅ Built-in

### Discord API Integration
- **Bot Permissions**: Requires bot token with appropriate Discord permissions
- **Guild Integration**: Server-specific commands and role management
- **Voice Channel Monitoring**: Optional voice channel activity tracking
- **Message and Embed Support**: Rich message formatting and interactive responses

### Hosting Platform Support
- **Pterodactyl Panel**: Configured for game server hosting panels
- **Railway/Heroku**: Cloud platform deployment ready
- **Replit**: Browser-based development environment support
- **Generic VPS**: Standard Linux server compatibility

### File System Dependencies
- **JSON File Storage**: Local file system access for data persistence
- **Log File Management**: Optional logging to local files
- **Configuration Files**: Read/write access to configuration files