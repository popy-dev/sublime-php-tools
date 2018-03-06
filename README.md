SublimeText PHP tools plugin
============================

Class constructor generator
---------------------------

Command : `PHP: Generate Constructor for Class`

Reads a class properties and their related docblock to generate a typehinted class constructor and
its docblock.

Planned/implemented features :

- [x] Exclude static properties
- [x] Alignment in dockbloc & affectations
- [x] Basic template
- [x] PHP7.1-like nullable types handling (`?type`)
- [ ] Counpound nullable types handling (`type|null`)


Class use checker
-----------------

Command : `PHP: Check Use`

Reads a file and tries to match any usage of classes then prints out a report on missing use or
non used use.

Matchers :

- [x] new Foo()
- [x] function (Foo $foo, Bar $bar)
- [x] Foo::bar() and Foo::BAR
- [x] class Foo extends Bar
- [x] class Foo imlements Bar, Baz
- [x] @Bar
- [ ] instanceof
- [ ] use FooTrait;

Bugs/Improvements:

- Traits are considered within the use list
- Use a real parser rather than regular expression as comments with code will be matched.
- new $class is getting parsed
