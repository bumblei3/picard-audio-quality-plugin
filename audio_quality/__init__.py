import logging
import subprocess
import re
from types import MethodType
import threading

log = logging.getLogger("picard.plugins.audio_quality")
log.setLevel(logging.INFO)
log.info("[audio_quality] Plugin-Modul wird ausgeführt!")

PLUGIN_NAME = "Audio Quality Analyzer"
PLUGIN_AUTHOR = "AI-Assistent"
PLUGIN_DESCRIPTION = "Analysiert die Audioqualität mit ffmpeg und speichert sie als Prozentwert im Tag 'audio_quality'."
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
    filename = getattr(file, 'filename', str(file))
    log.info(f"[audio_quality] Processing file: {filename}")
    codec, bitrate, samplerate = get_audio_info_ffmpeg(filename)
    if codec == 'unknown' and bitrate == 0 and samplerate == 0:
        log.warning(f"[audio_quality] Could not analyze {filename}")
        file.metadata['audio_quality'] = '0'
    else:
        quality = calculate_quality(codec, bitrate, samplerate)
        file.metadata['audio_quality'] = str(quality)
        log.info(f"[audio_quality] {filename}: Codec={codec}, Bitrate={bitrate}, Sample-Rate={samplerate} => Quality={quality}%")

def patch_tagger_add_files():
    try:
        import picard.tagger
        tagger = picard.tagger.Tagger.instance()
        log.info(f"[audio_quality] Tagger instance: {tagger}")

        original_add_files = tagger.add_files
        def patched_add_files(self, files, *args, **kwargs):
            files_list = list(files)
            log.info(f"[audio_quality] Patched add_files called with {len(files_list)} files: {[getattr(f, 'filename', str(f)) for f in files_list]}")
            result = original_add_files(files_list, *args, **kwargs)
            for file in files_list:
                try:
                    audio_quality_processor(file)
                except Exception as e:
                    log.error(f"[audio_quality] Fehler beim Verarbeiten von {getattr(file, 'filename', str(file))}: {e}")
            return result
        tagger.add_files = MethodType(patched_add_files, tagger)
        log.info("[audio_quality] Successfully patched Tagger.add_files")
    except Exception as e:
        log.error(f"[audio_quality] Fehler beim Patchen von Tagger.add_files: {e}", exc_info=True)

# Starte das Patchen nach 2 Sekunden Verzögerung
threading.Timer(2.0, patch_tagger_add_files).start()