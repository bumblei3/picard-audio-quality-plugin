# Audio Quality Analyzer – Picard Plugin

Dieses Plugin analysiert die Audioqualität von Musikdateien mit ffmpeg und speichert das Ergebnis als Prozentwert im Tag `audio_quality`.

## Features
- Analysiert Codec, Bitrate und Sample-Rate
- Bewertet die Qualität als Prozentwert (0–100)
- Speichert das Ergebnis als Tag `audio_quality`

## Installation
1. Stelle sicher, dass [ffmpeg](https://ffmpeg.org/) installiert ist und im Systempfad liegt.
2. Kopiere den Ordner `audio_quality` in deinen Picard-Plugin-Ordner:
   - Unter Linux: `~/.config/MusicBrainz/Picard/plugins/`
   - Unter Windows: `%APPDATA%\MusicBrainz\Picard\plugins\`
3. Starte Picard neu und aktiviere das Plugin unter „Extras → Plugins“.

## Nutzung
- Lade Audiodateien in Picard.
- Das Plugin analysiert die Dateien beim Hinzufügen und setzt das Tag `audio_quality`.
- Speichere die Datei, um das Tag dauerhaft zu schreiben.

## Hinweise
- Das Plugin ist für Picard 3.x (Qt6) im Entwicklungsstadium gedacht.
- Die Plugin-API kann sich ändern – Feedback willkommen!

## Lizenz
MIT License 