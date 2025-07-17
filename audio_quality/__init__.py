import logging
import os
import subprocess
import re
from types import MethodType
import threading
from picard.extension_points.event_hooks import register_file_post_load_processor as picard_register_file_post_load_processor
from picard.extension_points.metadata import register_album_metadata_processor as picard_register_album_metadata_processor
from picard.extension_points.event_hooks import register_file_post_save_processor as picard_register_file_post_save_processor

# Eigenes File-Logging einrichten
logfile = os.path.expanduser("~/audio_quality_plugin.log")
file_handler = logging.FileHandler(logfile, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler.setFormatter(formatter)

log = logging.getLogger("audio_quality_plugin")
log.setLevel(logging.DEBUG)
if not log.hasHandlers():
    log.addHandler(file_handler)
log.info("[audio_quality] Plugin wurde geladen und Logger initialisiert!")

# Test: Kann ffmpeg aufgerufen werden?
try:
    out = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    log.info("[audio_quality] ffmpeg test: " + out.stdout.splitlines()[0])
except Exception as e:
    log.error(f"[audio_quality] ffmpeg test failed: {e}")

PLUGIN_NAME = "Audio Quality Analyzer"
PLUGIN_AUTHOR = "Dein Name"
PLUGIN_DESCRIPTION = "Analysiert die Audioqualität von Musikdateien."
PLUGIN_VERSION = "0.1"
PLUGIN_API_VERSIONS = ["3.0"]

CODEC_SCORES = {
    'flac': 100, 'wav': 100, 'alac': 100, 'ape': 100, 'wv': 100,
    'mp3': 60, 'aac': 80, 'ogg': 75, 'opus': 85, 'wma': 70,
}

BITRATE_BONUS = [
    (320, 30), (256, 20), (192, 10), (128, 0), (0, -20),
]

SAMPLERATE_BONUS = [
    (48000, 5), (44100, 0), (0, -10),
]

def get_audio_info_ffmpeg(filename):
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", filename],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
        )
        output = result.stderr
        codec_match = re.search(r'Audio: ([^,]+)', output)
        codec = codec_match.group(1).lower().strip() if codec_match else 'unknown'
        bitrate_match = re.search(r'(\d+) kb/s', output)
        bitrate = int(bitrate_match.group(1)) if bitrate_match else 0
        samplerate_match = re.search(r'(\d+) Hz', output)
        samplerate = int(samplerate_match.group(1)) if samplerate_match else 0
        return codec, bitrate, samplerate
    except Exception as e:
        log.error(f"[audio_quality] Fehler bei ffmpeg: {e}")
        return 'unknown', 0, 0

def calculate_quality(codec, bitrate, samplerate):
    score = CODEC_SCORES.get(codec, 40)
    for br, bonus in BITRATE_BONUS:
        if bitrate >= br:
            score += bonus
            break
    for sr, bonus in SAMPLERATE_BONUS:
        if samplerate >= sr:
            score += bonus
            break
    return max(0, min(100, score))

def audio_quality_processor(file):
    log.info(f"[audio_quality] Processing file: {getattr(file, 'filename', str(file))}")
    filename = getattr(file, 'filename', str(file))
    codec, bitrate, samplerate = get_audio_info_ffmpeg(filename)
    if codec == 'unknown' and bitrate == 0 and samplerate == 0:
        log.warning(f"[audio_quality] Could not analyze {filename}")
        file.metadata['audio_quality'] = '0'
    else:
        quality = calculate_quality(codec, bitrate, samplerate)
        file.metadata['audio_quality'] = str(quality)
        log.info(f"[audio_quality] {filename}: Codec={codec}, Bitrate={bitrate}, Sample-Rate={samplerate} => Quality={quality}%")

def analyze_audio_quality(file_path):
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", file_path],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        for line in result.stderr.splitlines():
            if "bitrate:" in line:
                parts = line.split("bitrate:")
                if len(parts) > 1:
                    value = parts[1].split()[0]
                    return value  # z.B. "320"
        return "unbekannt"
    except Exception as e:
        return f"Fehler: {e}"

def set_quality_tags(file, quality, context=""):
    if hasattr(file, 'metadata') and hasattr(file.metadata, '__setitem__'):
        file.metadata['audio_quality'] = str(quality)
        file.metadata['comment'] = f"Audio Quality: {quality}% {context}"  # Standard-Tag
        log.info(f"[audio_quality] {context} Tags gesetzt: audio_quality={quality}, comment=Audio Quality: {quality}%")
    else:
        log.warning(f"[audio_quality] {context} Konnte Tags nicht setzen für Datei: {getattr(file, 'filename', str(file))}")

# Im File-Processor:
def register_file_post_load_processor(tagger):
    log.info("[audio_quality] register_file_post_load_processor wurde aufgerufen!")
    def process(file):
        try:
            file_path = getattr(file, 'filename', None)
            if file_path:
                qual = analyze_audio_quality(file_path)
                file.metadata['audio_quality'] = qual
            else:
                file.metadata['audio_quality'] = 'unbekannt'
            file.update()
            log.info(f"[audio_quality] Tag 'audio_quality' gesetzt: {file.metadata['audio_quality']} für Datei: {file_path}")
        except Exception as e:
            log.error(f"[audio_quality] Fehler beim Setzen der Tags: {e}")
    picard_register_file_post_load_processor(process)
    # Logging: Was ist jetzt in der globalen Hook-Liste?
    try:
        import picard.file
        with open(os.path.expanduser("~/plugin_hook_debug.log"), "a") as f:
            f.write(f"Nach Registrierung: {picard.file.file_post_load_processors.functions}\n")
    except Exception as e:
        log.error(f"[audio_quality] Fehler beim Hook-Logging: {e}")

def register_album_action(tagger):
    pass

def register_track_action(tagger):
    pass

def register_file_post_save_processor(tagger):
    log.info("[audio_quality] register_file_post_save_processor wurde aufgerufen!")
    def process(file):
        try:
            log.info(f"[audio_quality] post_save für Datei: {getattr(file, 'filename', str(file))}")
            if hasattr(file, 'metadata'):
                log.info(f"[audio_quality] post_save Metadaten: {dict(file.metadata)}")
            else:
                log.warning(f"[audio_quality] post_save: Keine Metadaten für Datei: {getattr(file, 'filename', str(file))}")
        except Exception as e:
            log.error(f"[audio_quality] Fehler im post_save-Processor: {e}")
    picard_register_file_post_save_processor(process)

# Im Album-Processor:
def register_album_metadata_processor(tagger):
    log.info("[audio_quality] register_album_metadata_processor wurde aufgerufen!")
    def process(album, metadata, release):
        try:
            log.info(f"[audio_quality] MINIMALTEST: Album geladen: {getattr(album, 'album', str(album))}")
        except Exception as e:
            log.error(f"[audio_quality] Fehler im Minimaltest: {e}")
    picard_register_album_metadata_processor(process)

def load_plugin(tagger):
    with open(os.path.expanduser("~/plugin_load_debug.log"), "a") as f:
        f.write("load_plugin wurde aufgerufen!\n")
    register_file_post_load_processor(tagger)
    # Optional: weitere Initialisierung (z.B. weitere Hooks registrieren)