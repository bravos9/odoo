# -*- coding: utf-8 -*-
import abc
import contextlib
import fnmatch
import io

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList
from sphinx import addnodes
from sphinx.ext.autodoc import members_set_option, bool_option, ALL

from autojsdoc.ext.extractor import read_js
from ..parser import jsdoc


@contextlib.contextmanager
def addto(parent, newnode):
    assert isinstance(newnode, nodes.Node), \
        "Expected newnode to be a Node, got %s" % (type(newnode))
    yield newnode
    parent.append(newnode)


def documenter_for(directive, modname, classname, doc):
    if isinstance(doc, jsdoc.ClassDoc):
        return ClassDocumenter(directive, modname, None, doc)
    if isinstance(doc, jsdoc.NSDoc):
        return NSDocumenter(directive, modname, None, doc)
    if isinstance(doc, jsdoc.MixinDoc):
        return MixinDocumenter(directive, modname, None, doc)
    if isinstance(doc, jsdoc.FunctionDoc):
        return FunctionDocumenter(directive, modname, classname, doc)
    if isinstance(doc, (jsdoc.PropertyDoc, jsdoc.LiteralDoc)):
        return PropertyDocumenter(directive, modname, classname, doc)
    if isinstance(doc, jsdoc.InstanceDoc):
        return InstanceDocumenter(directive, modname, classname, doc)
    if isinstance(doc, jsdoc.Unknown):
        return UnknownDocumenter(directive, None, None, doc)

    raise TypeError("No documenter for %s" % type(doc))
def doc_for(directive, modname, classname, doc):
    return documenter_for(directive, modname, classname, doc).generate()

def to_list(doc, source=None):
    return StringList([
        line.rstrip('\n')
        for line in io.StringIO(doc)
    ], source=source)
def automodule_bound(app, modules, symbols):
    class AutoModuleDirective(Directive):
        required_arguments = 1
        has_content = True
        option_spec = {
            'members': members_set_option,
            'undoc-members': bool_option,
            'private-members': bool_option,
            'undoc-matches': bool_option,
        }

        # self.state.nested_parse(string, offset, node) => parse context for sub-content (body which can contain RST data)
        # => needed for doc (converted?) and for actual directive body
        def run(self):
            modname = self.arguments[0].strip()

            # TODO: cache/memoize modules & symbols?
            if not modules:
                read_js(app, modules, symbols)

            mods = [
                (name, mod)
                for name, mod in modules.items()
                if fnmatch.fnmatch(name, modname)
            ]
            ret = []
            for name, mod in mods:
                if name != modname and not (mod.doc or mod.exports):
                    # this module has no documentation, no exports and was
                    # not specifically requested through automodule -> skip
                    # unless requested
                    if not self.options.get('undoc-matches'):
                        continue
                modsource = mod['sourcefile']
                if modsource:
                    self.state.document.settings.env.note_dependency(modsource)
                # FIXME: not sure what that's used for as normal xrefs are resolved using the id directly
                target = nodes.target('', '', ids=['module-' + name], ismod=True)
                self.state.document.note_explicit_target(target)

                documenter = ModuleDocumenter(self, None, None, mod)

                ret.append(target)
                ret.extend(documenter.generate())
            return ret

    return AutoModuleDirective
# FIXME: autoclass/automethod/autofunction/autons/automixin/... directive
class Documenter(object):
    objtype = None
    def __init__(self, directive, mod, classname, doc):
        self._directive = directive
        self._module = mod
        self._class = classname
        self._doc = doc
    def generate(self):
        """
        :rtype: List[nodes.Node]
        """
        objname = self._doc.name
        objtype = self.objtype
        assert objtype, '%s has no objtype' % type(self)
        root = addnodes.desc(domain='js', desctype=objtype, objtype=objtype)
        with addto(root, addnodes.desc_signature(
            module=self._module or '',
            fullname=objname,
        )) as s:
            s['class'] = self._class or ''

            if objname:
                s['ids'] = [objname]
            if objtype:
                s += addnodes.desc_annotation(
                    objtype, objtype,
                    nodes.Text(' '),
                )
            if objname and objtype:
                env = self._directive.state.document.settings.env
                env.domaindata['js']['objects'][objname] = (env.docname, objtype)

            # TODO: linkcode_resolve
            s += self.make_signature()
        with addto(root, addnodes.desc_content()) as c:
            c += self.make_content()
        return [root]

    @abc.abstractmethod
    def make_signature(self):
        """
        :rtype: List[nodes.Node]
        """
    @abc.abstractmethod
    def make_content(self):
        """
        :rtype: List[nodes.Node]
        """

    def should_document(self, member):
        """
        :type member: jsdoc.CommentDoc
        :rtype: bool
        """
        options = self._directive.options
        member_name = member.name

        members = options.get('members')
        if members is not ALL:
            # if a member is requested by name, it's always documented
            return member_name in members

        # ctor params are merged into the class doc
        if member.is_constructor:
            return False

        # only document "private" members if option is set
        if member.is_private and not options.get('private-members'):
            return False

        # TODO: what if member doesn't have a description but has non-desc tags set?
        return bool(member.doc or options.get('undoc-members'))

class ModuleDocumenter(Documenter):
    objtype = 'module'
    def make_signature(self):
        return [addnodes.desc_name(self._doc.name, self._doc.name)]
    def make_content(self):
        doc = self._doc
        content = addnodes.desc_content()

        self._directive.state.nested_parse(self._directive.content, 0, content)

        if doc.doc:
            # FIXME: source offset
            self._directive.state.nested_parse(to_list(doc.doc, source=doc['sourcefile']), 0, content)

        if doc.dependencies:
            with addto(content, nodes.field_list()) as fields:
                with addto(fields, nodes.field()) as field:
                    self.make_dependencies(field, doc)

        # FIXME: xref exports to exported object (unless anonymous?)
        # FIXME: document all elements in bodies based on :members:, undoc, private
        if doc.exports:
            content += doc_for(self._directive, doc.name, None, doc.exports)

        return content

    def make_dependencies(self, field, doc):
        field += nodes.field_name("Depends On", "Depends On")
        with addto(field, nodes.field_body()) as body:
            with addto(body, nodes.bullet_list()) as deps:
                for dep in doc.dependencies:
                    ref = addnodes.pending_xref(
                        dep, nodes.paragraph(dep, dep),
                        reftype='module',
                        reftarget=dep,
                        refdomain='js',
                    )
                    # TODO: js:module/js:object keys for relative lookup
                    deps += nodes.list_item(dep, ref)


class ClassDocumenter(Documenter):
    objtype = 'class'
    def make_signature(self):
        return [
            addnodes.desc_name(self._doc.name, self._doc.name),
            self.make_parameters(),
        ]

    def make_parameters(self):
        params = addnodes.desc_parameterlist('', '')
        ctors = self._doc.constructors
        if not ctors:
            return params
        for p in ctors[0].params:
            name = p.name.strip()
            if name.startswith('[') and name.startswith(']'):
                n = name[1:-1]
                params += addnodes.desc_optional(n, n)
            else:
                params += addnodes.desc_parameter(name, name)
        return params

    def make_content(self):
        doc = self._doc
        ret = nodes.section()
        if doc.doc:
            self._directive.state.nested_parse(to_list(doc.doc), 0, ret)
        # FIXME: fields params doc from ctor
        # FIXME: split & xref ctor params

        if doc.mixins:
            with addto(ret, nodes.field_list()) as fields:
                with addto(fields, nodes.field()) as field:
                    field += self.make_mixins()

        for m in doc.methods:
            if not self.should_document(m):
                continue

            ret += doc_for(self._directive, self._module, self._doc.name, m)

        return ret.children

    def make_mixins(self):
        ret = nodes.section('', nodes.field_name("Mixes", "Mixes"))
        with addto(ret, nodes.field_body()) as body:
            with addto(body, nodes.bullet_list()) as mixins:
                for mixin in self._doc.mixins:
                    mixins += nodes.list_item('', nodes.paragraph(mixin.name, mixin.name))
        return ret.children

class InstanceDocumenter(Documenter):
    objtype = 'object'
    def make_signature(self):
        cls = self._doc.cls
        if not cls:
            return [addnodes.desc_name(self._doc.name, self._doc.name)]

        return [
            addnodes.desc_name(self._doc.name, self._doc.name),
            addnodes.desc_annotation(' instance of ', ' instance of '),
            # FIXME: xref class
            addnodes.desc_type(cls.name, cls.name),
        ]

    def make_content(self):
        ret = nodes.section()
        if self._doc.doc:
            self._directive.state.nested_parse(to_list(self._doc.doc), 0, ret)
            return ret.children
        return ret.children

class FunctionDocumenter(Documenter):
    @property
    def objtype(self):
        return 'method' if self._class else 'function'
    def make_signature(self):
        # FIXME: xref superclass
        ret = nodes.section('', addnodes.desc_name(self._doc.name, self._doc.name))
        # TODO: desc_annotation, desc_type?
        with addto(ret, addnodes.desc_parameterlist()) as params:
            # FIXME: guess params if undoc'd
            for p in self._doc.params:
                name = p.name.strip()
                # FIXME: extract sub-params to typedef (in body?)
                if '.' in name:
                    continue
                if name.startswith('[') and name.startswith(']'):
                    n = name[1:-1]
                    params += addnodes.desc_optional(n, n)
                else:
                    params += addnodes.desc_parameter(name, name)
        retval = self._doc.return_val
        if retval.type or retval.doc:
            ret += addnodes.desc_returns(retval.type or '*', retval.type  or '*')
        return ret.children

    def make_content(self):
        ret = nodes.section()
        doc = self._doc
        if doc.doc:
            self._directive.state.nested_parse(to_list(doc.doc), 0, ret)

        if doc.params or doc.return_val.type or doc.return_val.doc:
            with addto(ret, nodes.field_list()) as fields:
                if doc.params:
                    with addto(fields, nodes.field()) as field:
                        field += nodes.field_name('Parameters', 'Parameters')
                        with addto(field, nodes.field_body()) as body,\
                             addto(body, nodes.bullet_list()) as holder:
                            holder.extend(self.make_parameters(doc.params))
                if doc.return_val.doc:
                    with addto(fields, nodes.field()) as field:
                        field += nodes.field_name("Returns", "Returns")
                        with addto(field, nodes.field_body()) as body,\
                             addto(body, nodes.paragraph()) as p:
                            p += nodes.inline(doc.return_val.doc, doc.return_val.doc)
                if doc.return_val.type:
                    # FIXME: split & xref return type
                    with addto(fields, nodes.field()) as field:
                        field += nodes.field_name("Return Type", "Return Type")
                        with addto(field, nodes.field_body()) as body, \
                             addto(body, nodes.paragraph()) as p:
                            p += nodes.inline(doc.return_val.type, doc.return_val.type)
        return ret.children

    def make_parameters(self, params):
        for param in params:
            name = param.name.strip().strip('[]')
            p = nodes.paragraph(
                '', '', addnodes.literal_strong(name, name))
            if param.type:
                # FIXME: split & xref param type
                p += [
                    nodes.Text(' ('),
                    addnodes.literal_emphasis(param.type, param.type),
                    nodes.Text(')'),
                ]
            if param.doc:
                p += [
                    nodes.Text(' -- '),
                    nodes.inline(param.doc, param.doc)
                ]
            yield p

class ObjectDocumenter(Documenter):
    def make_signature(self):
        if self._doc.name:
            return [addnodes.desc_name(self._doc.name, self._doc.name)]
        return []
    def make_content(self):
        doc = self._doc
        ret = nodes.section()
        if doc.doc:
            self._directive.state.nested_parse(to_list(doc.doc), 0, ret)
        # FIXME: xref when property is named/not inline
        for (_, p) in doc.properties:
            if not self.should_document(p):
                continue
            ret += doc_for(self._directive, self._module, None, p)
        return ret.children

class NSDocumenter(ObjectDocumenter):
    objtype = 'namespace'
class MixinDocumenter(ObjectDocumenter):
    objtype = 'mixin'

# FIXME: add typedef support

class PropertyDocumenter(Documenter):
    objtype = 'attribute'
    def make_signature(self):
        return [addnodes.desc_name(self._doc.name, self._doc.name)]

    def make_content(self):
        doc = self._doc
        ret = nodes.section()
        if doc.doc:
            self._directive.state.nested_parse(to_list(doc.doc), 0, ret)
        # FIXME: type?
        return ret.children

class UnknownDocumenter(Documenter):
    objtype = 'unknown'
    def make_signature(self):
        return [addnodes.desc_name(self._doc.name, self._doc.name)]
    def make_content(self):
        return []
