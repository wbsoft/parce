The livelex Python module
=========================

This module is designed to parse text using rules, which are regular-expression 
based. Rules are grouped into lexicons, and lexicons are grouped into a 
Language object. Every lexicon has its own set of rules that describe the text 
that is expected in that context.

A rule consists of three parts: a pattern, an action and a target.

* The pattern is a either a regular expression string, or an object that 
  inherits Pattern. In that case its build() method is called to get the 
  pattern.

* The action can be any object, and is streamed together with the matched part 
  of the text. It can be seen as a token. If the action is an instance of 
  Action, its filter_actions() method is called, which can yield zero or more 
  tokens.  The special `skip` action skips the matching text.

* The target is a list of objects, which can be integer numbers or references
  to a different lexicon. A positive number pushes the same lexicon on the 
  stack, while a negative number pops the current lexicon(s) off the stack, so 
  that lexing the text continues with a previous lexicon. It is also possible 
  to pop a lexicon and push a different one.

Using a special rule, a lexicon may specify a default action, which is 
streamed with text that is not recognized by any other rule in the lexicon.
A lexicon may also specify a default target, which is chosen when no rule
matches the current text.

The livelex module is written and maintained by Wilbert Berendsen.
