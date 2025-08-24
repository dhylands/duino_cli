"""
Adds completion support.
"""
import argparse

from typing import Callable, Iterable, List

from argcomplete.finders import CompletionFinder
from argcomplete.lexers import split_line

from prompt_toolkit.completion import CompleteEvent, Completer, Completion, WordCompleter

from duino_cli.command_argument_parser import CommandArgumentParser


class ArgFinder(CompletionFinder):
    """argcomplete completer."""

    def get_completions(self, argument_parser: argparse.ArgumentParser, line: str,
                        cursor_posn: int) -> List[str]:
        """Returns completions corresponding to the cursor position."""
        super().__init__(argument_parser=argument_parser)
        if self._parser is None:
            raise ValueError('Must provide an argument parser')
        cword_prequote, cword_prefix, _cword_suffix, comp_words, last_wordbreak_pos = split_line(
            line, cursor_posn)
        start = 1
        comp_words = comp_words[start:]
        if cword_prefix and cword_prefix[0] in self._parser.prefix_chars and "=" in cword_prefix:
            # Special case for when the current word is "--optional=PARTIAL_VALUE".
            # Give the optional to the parser.
            comp_words.append(cword_prefix.split("=", 1)[0])
        completions = self._get_completions(comp_words, cword_prefix, cword_prequote,
                                            last_wordbreak_pos)
        #print(f'completions = {completions}')
        return completions


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
        #print(f'text = {text}')
        #stripped_len = len(document.text_before_cursor) - len(text)

        if ' ' not in text:
            yield from self.cmd_completer.get_completions(document, complete_event)
            return

        finder = ArgFinder()

        cmd = text.split()[0]
        # print(f'get_completions: cmd = {cmd}')
        parser = self.create_argparser(cmd)
        # print(f'get_completions: parser = {parser}')
        completions = finder.get_completions(parser, document.text_before_cursor,
                                             document.cursor_position)
        word_completer = WordCompleter(completions)
        yield from word_completer.get_completions(document, complete_event)


# os.environ['_ARC_DEBUG'] = '1'
