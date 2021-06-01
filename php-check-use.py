import sublime
import sublime_plugin
import re
import os
from os import listdir
from os.path import isfile, join


def log(msg):
    print("[PHP Check Use] %s" + msg)


class UseDefCollection():
    def __init__(self, start=[]):
        self.list = start
        self.known = []

    def getAll(self):
        for a in self.list:
            if not a.dynamic:
                yield a

    def append(self, definition):
        if not definition.shortName in self.known:
            self.list.append(definition)
            self.known.append(definition.shortName)

    def hasUse(self, definition):
        for a in self.list:
            if a.hasUse(definition):
                return True

        return False

    def debug(self):
        for a in self.list:
            z = ' Not Dynamic '

            if a.dynamic:
                z = ' Dynamic '

            log(a.name + z + a.shortName)


class UseDef():
    def __init__(self, name, dynamic=False):
        self.name = name
        self.dynamic = dynamic
        self.shortName = self.name.split('\\')[-1]

    def getShortName(self):
        return self.shortName

    def hasUse(self, usage):
        return usage.lastUsable == self.shortName


class UseUsageCollection():
    def __init__(self, start=[]):
        self.list = start
        self.known = []

    def getAll(self):
        for a in self.list:
            if a.name not in ['string', 'array', 'integer', 'boolean', 'float', 'static', 'self', 'parent']:
                yield a

    def append(self, usage):
        if not usage.lastUsable in self.known:
            self.list.append(usage)
            self.known.append(usage.lastUsable)

    def isUsed(self, definition):
        for a in self.getAll():
            if a.isUsed(definition):
                return True

        return False

    def debug(self):
        for a in self.list:
            log(a.name + ' ' + a.lastUsable)


class UseUsage():
    def __init__(self, name):
        self.name = name
        self.lastUsable = self.name.split('\\')[0]

    def isUsed(self, definition):
        return definition.shortName == self.lastUsable


class Output():
    def __init__(self, window):
        self.window = window
        self.inited = False

    def init(self):
        if self.inited:
            return

        self.view = self.window.new_file()
        self.view.set_scratch(True)
        self.view.set_syntax_file('Packages/Default/Find Results.hidden-tmLanguage')
        self.view.set_name("PHP Use Check")
        self.edit = self.view.begin_edit()
        self.cursor = 0
        self.inited = True

    def writeln(self, message, offset=0):
        self.init()

        message = " " * offset + message + "\n"
        self.view.insert(self.edit, self.view.text_point(self.cursor, 0), message)
        self.cursor = self.cursor + 1

    def finish(self):
        if not self.inited:
            return

        self.view.end_edit(self.edit)


class Commander():
    def __init__(self, view, window):
        self.view = view
        self.window = window

    def run(self):
        filename = self.view.file_name()
        content = open(filename).read()
        filepath = os.path.dirname(filename)

        uses = self.findDeclaredUse(content, filepath)
        used = self.findUsedUse(content)

        output = Output(self.window)

        errors = False

        # Check Missing uses
        missingUses = []

        for use in used.getAll():
            if not uses.hasUse(use):
                missingUses.append(use.lastUsable)

        if len(missingUses):
            output.writeln("Missing uses:")
            errors = True

            for a in missingUses:
                output.writeln(a, 4)

            output.writeln("")

        # Check too many uses
        overUsed = []

        for use in uses.getAll():
            if not used.isUsed(use):
                overUsed.append(use.name)

        if len(overUsed):
            errors = True
            output.writeln("Unused uses:")

            for a in overUsed:
                output.writeln(a, 4)

        if not errors:
            self.view.set_status("PHPCHECKUSE", "[PHP Check Use] All OK")

        output.finish()

    def findDeclaredUse(self, content, filepath):
        uses = UseDefCollection([])

        # use Foo\Bar. Fuck traits.
        pattern = re.compile(r'use\s([a-zA-Z\\\s,_]+);')
        res = pattern.finditer(content, re.MULTILINE)

        for a in res:
            for b in a.group(1).split(','):
                c = b.strip()

                if -1 != c.find(' as '):
                    spl = re.split('\sas\s', c)
                    uses.append(UseDef(spl[1], False))

                else:
                    uses.append(UseDef(c, False))

        # Files.php
        for f in listdir(filepath):
            if isfile(join(filepath, f)):
                n, ext = os.path.splitext(os.path.basename(f))

                if ext == '.php':
                    uses.append(UseDef(n, True))

        return uses

    def findUsedUse(self, content):
        used = UseUsageCollection([])

        ## new FooBar();
        pattern = re.compile(r'new\s+(?!\\)([^\(;\s]+)')  # Skips absolute namespaces
        res = pattern.finditer(content, re.MULTILINE)

        for a in res:
            used.append(UseUsage(a.group(1)))

        # (Request $request, Baz\Bar $z)
        pattern = re.compile(r'(?:\(|,\s*)[\n\s]*((?!\\)[a-zA-Z\\_]+)\s+\$')
        res = pattern.finditer(content, re.MULTILINE)

        for a in res:
            used.append(UseUsage(a.group(1)))

        # Tools::slugify
        pattern = re.compile(r'([a-zA-Z\\_]+)::')  # Can't match negative assertion
        res = pattern.finditer(content, re.MULTILINE)

        for a in res:
            r = a.group(1)

            if r[0] != '\\':
                used.append(UseUsage(a.group(1)))

        # class X extends Y
        pattern = re.compile(r'(?:class|interface)\s(?:[a-zA-Z_]+)\sextends\s([^\s]+)')  # limits risks of comments with that sentence
        res = pattern.finditer(content, re.MULTILINE)

        for a in res:
            used.append(UseUsage(a.group(1)))

        # implements list
        pattern = re.compile(r'implements\s([^{]+)')
        res = pattern.finditer(content, re.MULTILINE)

        for a in res:
            for b in a.group(1).split(','):
                c = b.strip()
                used.append(UseUsage(c))

        # Annotations
        pattern = re.compile(r'\@((?<!\\)[a-zA-Z\\_]+)(?:\(|\n)')
        res = pattern.finditer(content, re.MULTILINE)

        for a in res:
            used.append(UseUsage(a.group(1)))

        return used


class PhpToolsCheckUseCommand(sublime_plugin.WindowCommand):
    def run(self):
        if not self.isPhpSyntax():
            log('Only available in a PHP file')
            return

        self.view = self.window.active_view()
        commander = Commander(self.view, self.window)
        commander.run()

    def is_enabled(self):
        return self.isPhpSyntax()

    def is_visible(self):
        return self.isPhpSyntax()

    def isPhpSyntax(self):
        return re.search(".*\PHP", self.window.active_view().settings().get('syntax')) is not None
