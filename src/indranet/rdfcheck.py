"""Deliberately bounded SHACL property-constraint evaluator.

Supports targetClass, simple IRI paths, min/maxCount, datatype, nodeKind IRI,
and in. Unsupported constraint predicates raise instead of silently passing.
This is not a complete SHACL engine or an entailment implementation.
"""
from rdflib import Graph, URIRef, Literal, RDF, XSD, Namespace
from .canon import ContractError
SH=Namespace('http://www.w3.org/ns/shacl#')

def validate(data: Graph, shapes: Graph) -> list[dict]:
    failures=[]
    allowed={RDF.type,SH.targetClass,SH.property,SH.path,SH.minCount,SH.maxCount,SH.datatype,SH.nodeKind,SH['in']}
    for _,predicate,_ in shapes:
        if str(predicate).startswith(str(SH)) and predicate not in allowed:
            raise ContractError('Unsupported SHACL predicate: '+str(predicate))
    for shape in shapes.subjects(RDF.type,SH.NodeShape):
        for target in shapes.objects(shape,SH.targetClass):
            for focus in data.subjects(RDF.type,target):
                for prop in shapes.objects(shape,SH.property):
                    path=shapes.value(prop,SH.path)
                    if not isinstance(path,URIRef): raise ContractError('Only simple property paths are supported')
                    values=list(data.objects(focus,path))
                    minimum=shapes.value(prop,SH.minCount);maximum=shapes.value(prop,SH.maxCount)
                    def fail(code): failures.append({'focus':str(focus),'path':str(path),'constraint':code})
                    if minimum is not None and len(values)<int(minimum): fail('minCount')
                    if maximum is not None and len(values)>int(maximum): fail('maxCount')
                    datatype=shapes.value(prop,SH.datatype);kind=shapes.value(prop,SH.nodeKind);choices=shapes.value(prop,SH['in'])
                    permitted=set(shapes.items(choices)) if choices else None
                    for value in values:
                        if datatype is not None:
                            actual=(value.datatype or XSD.string) if isinstance(value,Literal) and value.language is None else None
                            if actual!=datatype or (datatype==XSD.dateTime and isinstance(value.toPython(),Literal)): fail('datatype')
                        if kind is not None:
                            if kind!=SH.IRI: raise ContractError('Only sh:IRI nodeKind is supported')
                            if not isinstance(value,URIRef): fail('nodeKind')
                        if permitted is not None and value not in permitted: fail('in')
    return failures
