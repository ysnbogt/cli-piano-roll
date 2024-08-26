import argparse
import os
import subprocess
import sys
import time
from shutil import get_terminal_size
from typing import Any, Callable

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import pygame
from colorama import Back, Fore, Style
from mido import MidiFile, tempo2bpm


class PianoRoll:
    note_text = " █"
    padding = "  "
    padding_with_border = "│ "
    num_rows = 88

    def __init__(
        self,
        file_path: str,
        border: bool = True,
        color: bool = True,
        keyboard: bool = True,
        play: bool = True,
        resolution: int = 10,
    ) -> None:
        self.file_path = file_path
        self.border = border
        self.color = color
        self.keyboard = keyboard
        self.play = play
        self.resolution = resolution

        self.white_key_color = Fore.LIGHTCYAN_EX
        self.black_key_color = Fore.GREEN
        self.border_color = Fore.LIGHTBLACK_EX

    @staticmethod
    def is_white_key(note: int) -> bool:
        white_keys = {0, 2, 4, 5, 7, 9, 11}
        return (note % 12) in white_keys

    @staticmethod
    def print_keyboard() -> None:
        octaves = 7
        sharp_keys = "  #  │" + "  #   #  │  #   #   #  │" * octaves + "  "
        flat_keys = "  ▏  │" + "  ▕   ▏  │  ▕   │   ▏  │" * octaves + "  "

        # Blank space is for adjustment
        line_start = " " + Back.WHITE + Fore.LIGHTBLACK_EX
        line_end = Style.RESET_ALL

        def print_line(text: str) -> None:
            print(line_start + text + line_end, flush=True)

        for _ in range(4):
            print_line(sharp_keys.replace("#", f"{Back.BLACK} {Back.WHITE}"))

        for _ in range(2):
            print_line(flat_keys)

    @staticmethod
    def get_terminal_size() -> tuple[int, int]:
        terminal_size = get_terminal_size()
        width = terminal_size.columns
        height = terminal_size.lines
        return width, height

    def _get_color_code(self, note: int) -> str:
        color_code = (
            self.white_key_color if self.is_white_key(note) else self.black_key_color
        )
        return color_code

    def _calculate_scroll_speed(self, bpm: int) -> float:
        # TODO: Values are not exact
        return -0.0005 * bpm + 0.1

    def display(self) -> None:
        midi = MIDI(self.file_path)
        notes = midi.get_notes()
        ticks_per_beat = midi.get_ticks_per_beat()

        piano_roll = self.generate(notes=notes, ticks_per_beat=ticks_per_beat)

        if self.play:
            scroll_speed = self._calculate_scroll_speed(midi.get_bpm())
            _, height = self.get_terminal_size()

            for start_row in range(len(piano_roll) - height, -1, -1):
                subprocess.run(["tput", "civis"], check=True)
                sys.stdout.write("\033[H")

                for row in piano_roll[start_row : start_row + height]:
                    print("".join(row) + " ", flush=True)

                if self.keyboard:
                    self.print_keyboard()

                sys.stdout.write("\033[0K" * 1)
                sys.stdout.write("\033[A" * 1)

                time.sleep(scroll_speed)
        else:
            for row in piano_roll:
                print("".join(row).rstrip())

            if self.keyboard:
                self.print_keyboard()

    def generate(
        self,
        notes: list[tuple[int, int]],
        ticks_per_beat: int,
    ) -> Any:
        num_cols = len(notes)
        piano_roll = [["" for _ in range(num_cols)] for _ in range(self.num_rows)]

        note_end_times = {}
        for note, tick in notes:
            if tick not in note_end_times:
                note_end_times[tick] = []
            note_end_times[tick].append(note)

        for start_tick, notes_on in note_end_times.items():
            for note in notes_on:
                row = 108 - note
                col = start_tick // (ticks_per_beat // self.resolution)
                color_code = self._get_color_code(note) if self.color else ""
                if 0 <= row < self.num_rows and 0 <= col < num_cols:
                    piano_roll[row][col] = color_code + self.note_text

        def is_border_required(num: int) -> bool:
            b_c = (num - (self.num_rows - 4)) % 12 == 0
            e_f = (num - (self.num_rows - 9)) % 12 == 0
            return self.border and (b_c or e_f)

        for i, row in enumerate(piano_roll):
            start = False
            text = ""
            for j, note in enumerate(row):
                if self.note_text in note:
                    start = not start
                    text = note

                piano_roll[i][j] = self.padding
                if is_border_required(i):
                    piano_roll[i][j] = self.border_color + self.padding_with_border
                if start:
                    piano_roll[i][j] = text

        piano_roll = [[row[i] for row in piano_roll] for i in range(len(piano_roll[0]))]
        piano_roll = [row[::-1] for row in piano_roll]
        piano_roll = piano_roll[::-1]

        return piano_roll

    def play_with_music(self) -> None:
        player = MusicPlayer(self.file_path)
        player.play_music(self.display)


class MIDI:
    def __init__(self, file_path: str) -> None:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file at {file_path} was not found.")

        self.file_path = file_path
        self.midi = MidiFile(file_path)

    def get_bpm(self) -> int:
        for track in self._get_tracks():
            for message in track:
                if message.type == "set_tempo":
                    tempo = message.tempo
                    bpm = tempo2bpm(tempo)
                    return int(bpm)

        return None

    def _get_tracks(self) -> Any:
        return self.midi.tracks

    def get_ticks_per_beat(self) -> int:
        return self.midi.ticks_per_beat

    def get_notes(self) -> list[tuple[int, int]]:
        notes = []
        note_start = {}

        for track in self._get_tracks():
            time = 0
            for message in track:
                time += message.time
                if message.type == "note_on" and message.velocity > 0:
                    note_start[message.note] = time
                elif message.type == "note_off" or (
                    message.type == "note_on" and message.velocity == 0
                ):
                    if message.note in note_start:
                        notes.append((message.note, note_start[message.note]))
                        notes.append((message.note, time))
                        del note_start[message.note]

        return notes


class MusicPlayer:
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path

        self.frequency = 44_100
        self.bit_size = -16
        self.channels = 2
        self.buffer = 1_024

    def play_music(self, callback_function: Callable, *args: Any) -> None:
        pygame.mixer.init(self.frequency, self.bit_size, self.channels, self.buffer)
        pygame.mixer.music.set_volume(0.8)

        try:
            clock = pygame.time.Clock()
            pygame.mixer.music.load(self.file_path)
            pygame.mixer.music.play()

            callback_function(*args)

            while pygame.mixer.music.get_busy():
                clock.tick(60)
        except KeyboardInterrupt:
            pygame.mixer.music.fadeout(1_000)
            pygame.mixer.music.stop()
        raise SystemExit


def parse_arguments() -> Any:
    parser = argparse.ArgumentParser(
        description="Display a piano roll from a MIDI file and optionally play music."
    )
    parser.add_argument("file_path", help="Path to the MIDI file to be processed.")
    parser.add_argument(
        "-p",
        "--play",
        action="store_true",
        help="Animate the piano roll as it scrolls through the notes.",
    )
    parser.add_argument(
        "-k",
        "--keyboard",
        action="store_true",
        help="Display a keyboard layout below the piano roll.",
    )
    parser.add_argument(
        "-c",
        "--color",
        action="store_true",
        help="Show the piano roll with color coding for notes.",
    )
    parser.add_argument(
        "-b",
        "--border",
        action="store_true",
        help="Add borders around the piano roll display.",
    )
    parser.add_argument(
        "-m",
        "--music",
        action="store_true",
        help="Play the MIDI file alongside the piano roll animation.",
    )
    parser.add_argument(
        "-r",
        "--resolution",
        type=int,
        default=10,
        help="""Set the resolution of the piano roll.
        Only even numbers are allowed (default: 10).""",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    piano_roll = PianoRoll(
        file_path=args.file_path,
        border=args.border,
        color=args.color,
        keyboard=args.keyboard,
        play=args.play,
        resolution=args.resolution,
    )
    if args.music:
        piano_roll.play_with_music()
    else:
        piano_roll.display()


if __name__ == "__main__":
    main()
