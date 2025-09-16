"""
Adds completion support.
"""
import argparse

from typing import Callable, Iterable, List, Tuple

from argcomplete.finders import CompletionFinder
from argcomplete.lexers import split_line

from prompt_toolkit.completion import CompleteEvent, Completer, Completion, WordCompleter

from duino_cli.command_argument_parser import CommandArgumentParser


def get_second_word_index(text: str) -> Tuple[str, str, int]:
    """Returns the 1st and second words of `text` along with the index of the second word."""
    words = text.split()  # Split the string into a list of words
    if len(words) < 2:
        if len(words) == 0:
            return ('', '', -1)  # Return -1 if there isn't a second word
        return (words[0], '', len(words[0]))

    first_word = words[0]
    second_word = words[1]

    # Find the end of the first word, then search for the second word starting from there
    first_word_end_index = text.find(first_word) + len(first_word)
    second_word_start_index = text.find(second_word, first_word_end_index)

    return (first_word, second_word, second_word_start_index)


class ArgFinder(CompletionFinder):
    """argcomplete completer."""

    def get_completions(self, argument_parser: argparse.ArgumentParser, sub_cmd: str,
                        sub_text: str) -> List[str]:
        """Returns completions corresponding to the cursor position."""
        super().__init__(argument_parser=argument_parser)
        if self._parser is None:
            raise ValueError('Must provide an argument parser')
        cword_prequote, cword_prefix, _cword_suffix, comp_words, first_colon_pos = split_line(
            sub_text)
        comp_words.insert(0, sub_cmd)
        matches = self._get_completions(comp_words, cword_prefix, cword_prequote, first_colon_pos)
        # argcomplete sometimes puts trailing spaces on single matches.
        matches = [match.rstrip() for match in matches]
        # print(f'matches = {matches}')
        return matches


class CliCompleter(Completer):
    """Prompt toolkit completer."""

    def __init__(self, commands: List[str],
                 create_argparser: Callable[[str], CommandArgumentParser]) -> None:
        super().__init__()
        # print(f'CliCompleter: commands = {commands}')
        self.cmd_completer = WordCompleter(commands)
        self.create_argparser = create_argparser

    def get_completions(self, document, complete_event: CompleteEvent) -> Iterable[Completion]:
        text = document.text_before_cursor.lstrip()
        # print(f'text = {text}')
        #stripped_len = len(document.text_before_cursor) - len(text)

        if ' ' not in text:
            yield from self.cmd_completer.get_completions(document, complete_event)
            return

        cmd, sub_cmd, second_word_index = get_second_word_index(text)
        sub_text = text[second_word_index:]
        # print(f'cmd = {cmd} sub_cmd = {sub_cmd} sub_text = {sub_text}')

        # argcomplete modifies the parser, make sure we pass down a newly constructed
        # parser each time we use the CompletionFinder
        parser = self.create_argparser(cmd)
        completer = ArgFinder()
        matches = completer.get_completions(parser, sub_cmd, sub_text)
        word_completer = WordCompleter(matches)
        # print(f'xx matches = {matches}')
        yield from word_completer.get_completions(document, complete_event)


# os.environ['_ARC_DEBUG'] = '1'
