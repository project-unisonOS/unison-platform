#!/bin/bash
#
# Audio Testing Script for Unison
#
# Tests microphone and speaker functionality
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "═══════════════════════════════════════════════════════════"
echo "           Unison Audio Testing Script"
echo "═══════════════════════════════════════════════════════════"
echo

# Check audio tools
log_info "Checking audio tools..."
MISSING_TOOLS=()

if ! command -v aplay &> /dev/null; then
    MISSING_TOOLS+=("aplay")
fi

if ! command -v arecord &> /dev/null; then
    MISSING_TOOLS+=("arecord")
fi

if ! command -v pactl &> /dev/null; then
    MISSING_TOOLS+=("pactl")
fi

if [[ ${#MISSING_TOOLS[@]} -gt 0 ]]; then
    log_error "Missing audio tools: ${MISSING_TOOLS[*]}"
    log_info "Install with: sudo apt-get install alsa-utils pulseaudio-utils"
    exit 1
fi

log_success "All audio tools available"
echo

# List audio devices
log_info "Audio Devices:"
echo
echo "Playback devices:"
aplay -l 2>/dev/null || log_error "No playback devices found"
echo
echo "Capture devices:"
arecord -l 2>/dev/null || log_error "No capture devices found"
echo

# PulseAudio status
log_info "PulseAudio Status:"
if pgrep -x pulseaudio > /dev/null; then
    log_success "PulseAudio is running"
    pactl info | grep "Server Name\|Server Version\|Default Sink\|Default Source"
else
    log_error "PulseAudio is not running"
    log_info "Start with: pulseaudio --start"
fi
echo

# Test speaker
log_info "Speaker Test"
echo "This will play a 1000Hz tone for 2 seconds..."
read -p "Press Enter to continue..."

if speaker-test -t sine -f 1000 -l 1 2>&1 | head -n 5; then
    sleep 2
    killall speaker-test 2>/dev/null || true
    echo
    read -p "Did you hear the tone? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_success "Speaker test passed"
    else
        log_error "Speaker test failed"
    fi
else
    log_error "Speaker test failed to run"
fi
echo

# Test microphone
log_info "Microphone Test"
echo "This will record 3 seconds of audio and play it back..."
read -p "Press Enter to continue..."

TEMP_FILE="/tmp/unison_audio_test_$(date +%s).wav"

log_info "Recording... (speak now)"
if arecord -d 3 -f cd -t wav "$TEMP_FILE" 2>&1 | tail -n 3; then
    log_success "Recording complete"
    
    log_info "Playing back recording..."
    if aplay "$TEMP_FILE" 2>&1 | tail -n 3; then
        log_success "Playback complete"
        
        read -p "Did you hear your recording? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_success "Microphone test passed"
        else
            log_error "Microphone test failed"
        fi
    else
        log_error "Playback failed"
    fi
    
    rm -f "$TEMP_FILE"
else
    log_error "Recording failed"
fi
echo

# Volume levels
log_info "Volume Levels:"
if command -v amixer &> /dev/null; then
    echo "Master volume:"
    amixer get Master | grep -E "Playback.*%"
    echo
    echo "Capture volume:"
    amixer get Capture | grep -E "Capture.*%"
else
    log_warning "amixer not available"
fi
echo

# Permissions check
log_info "Permissions Check:"
if groups | grep -q audio; then
    log_success "Current user is in 'audio' group"
else
    log_warning "Current user is NOT in 'audio' group"
    log_info "Add with: sudo usermod -aG audio $USER"
    log_info "Then log out and back in"
fi
echo

# Summary
echo "═══════════════════════════════════════════════════════════"
log_info "Audio Test Complete"
echo "═══════════════════════════════════════════════════════════"
echo
echo "If tests failed, try:"
echo "  1. Check volume levels: alsamixer"
echo "  2. Restart PulseAudio: pulseaudio -k && pulseaudio --start"
echo "  3. Check permissions: groups (should include 'audio')"
echo "  4. Check device connections: aplay -l && arecord -l"
echo
