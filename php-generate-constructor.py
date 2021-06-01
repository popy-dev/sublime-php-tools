import sublime
import sublime_plugin
import re
import os
from os.path import dirname, realpath

PLUGIN_DIR = dirname(realpath(__file__))

def log(msg):
	print ("[PHP Constructors] " + msg)

class Template(object):
	def __init__(self, name):
		path = os.path.join(PLUGIN_DIR, 'templates', name)

		log("opening template " + path)

		self.content = open(path).read()

	def replace(self, args):
		return self.content % args


class Property:
	def __init__(self, name, type, comment):
		self.name = name
		self.type = type or ''
		self.comment = comment or ''

	def toParamAnnotation(self, nameLength, typeLength):
		npad = 1 + nameLength - len(self.name)
		tpad = 1 + typeLength - len(self.type)
		return self.type + (' ' * tpad) + '$' + self.name + (' ' * npad) + self.comment

	def toConstructorArgument(self, nameLength, typeLength):
		if self.type == '':
			return '$' + self.name

		res = self.type + ' $' + self.name
		if self.type[0:1] == '?':
			res = res[1:] + ' = null'
		return res

	def toPropertyAssign(self, nameLength, typeLength):
		npad = 1 + nameLength - len(self.name)
		return self.name + (' ' * npad) + '= $' + self.name

class PropertyCollection:
	def __init__(self):
		self.nameLength = 0
		self.typeLength = 0
		self.collection = []

	def append(self, property):
		self.nameLength = max(self.nameLength, len(property.name))
		self.typeLength = max(self.typeLength, len(property.type))
		self.collection.append(property)

	def __iter__(self):
		return iter(self.collection)

	def __len__(self):
		return len(self.collection)


# /\*\*\n
# (?:\s*\*\s+([^\n]+)\n)?
# (?:\s*\*[^\n]*\n)*
# \s*\*\s+@var\s+(\S+)(?:\s[^\n]*)?\n
# (?:\s*\*[^\n]*\n)*
# \s*\*/\n
# \s*(?:public|protected|private|var)\s+\$

class PhpToolsGenerateConstructorCommand(sublime_plugin.TextCommand):
	propertyPattern = '(?:/\*\*\n(?:\s*\*\s+([^\n]+)\n)?(?:\s*\*[^\n]*?\n)*\s*\*\s+@var\s+(\S+)(?:\s[^\n]*)?\n(?:\s*\*[^\n]*?\n)*\s*\*/)?\n\s*(?:public|protected|private|var)\s+\$([^=;=\s]+)'

	def run(self, edit):
		# TODO: Verify if constructor already exists and skip

		# Load settings for future usage
		settings = sublime.load_settings('php-constructors.sublime-settings')


		properties = self.getClassProperties()

		if len(properties):
			constructor = self.doGenerateConstructor(properties)
			self.view.run_command("insert_snippet", {"contents": constructor.replace('$', '\\$')})


	def getClassProperties(self):
		regions = self.view.find_all(self.propertyPattern, sublime.IGNORECASE)
		properties = PropertyCollection()

		for region in regions:
			content = self.view.substr(region)
			matches = re.search(self.propertyPattern, content, re.IGNORECASE)

			if matches != None:
				properties.append(Property(matches.group(3), matches.group(2), matches.group(1)))

		return properties

	def doGenerateConstructor(self, properties):
		template = "/**\n * Class constructor.\n%(docblock)s */\npublic function __construct(%(arguments)s)\n{\n%(affectations)s\n}\n"
		template = Template('constructor')
		docblock = []
		arguments = []
		affectations = []

		for property in properties:
			docblock.append('@param ' + property.toParamAnnotation(properties.nameLength, properties.typeLength))
			arguments.append(property.toConstructorArgument(properties.nameLength, properties.typeLength))
			affectations.append('$this->' + property.toPropertyAssign(properties.nameLength, properties.typeLength) + ';')

		return template.replace({
			'docblock'     : '\n * '.join(docblock),
			'arguments'    : ', '.join(arguments),
			'affectations' : '\n\t'.join(affectations)
		})

	def isPhpSyntax(self):
		return re.search(".*\PHP", self.view.settings().get('syntax')) is not None

	def is_enabled(self):
		return self.isPhpSyntax()

	def is_visible(self):
		return self.is_enabled()
