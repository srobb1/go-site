#!/usr/bin/env python3

__author__ = 'cjm'

import argparse
import yaml
from json import dumps

def main():

    parser = argparse.ArgumentParser(description='GO Metadata'
                                                 '',
                                     formatter_class=argparse.RawTextHelpFormatter)

    print("## AUTOGENERATED MAKEFILE\n")
    parser.add_argument('files',nargs='*')
    args = parser.parse_args()
    artifacts = []
    artifacts_by_dataset = {}
    for fn in args.files:
        f = open(fn, 'r')
        obj = yaml.load(f)
        artifacts.extend(obj['datasets'])
        f.close()
    for a in artifacts:
        if 'source' not in a:
            # TODO
            print("## WARNING: no source for: {}".format(a['id']))
            continue
        ds = a['dataset']
        if ds == 'paint':
            print("## WARNING: Skipping PAINT: {}".format(a['id']))
            # TODO
            continue
        if ds == 'rnacentral':
            print("## WARNING: Skipping RNAC: {}".format(a['id']))
            # TODO
            continue

        if ds not in artifacts_by_dataset:
            artifacts_by_dataset[ds] = []
        artifacts_by_dataset[ds].append(a)

    for (ds,alist) in artifacts_by_dataset.items():
        generate_targets(ds, alist)
    targets = [all_files(ds) for ds in artifacts_by_dataset.keys()]
    rule('all_targets', ' '.join(targets), 'echo done')

def generate_targets(ds, alist):
    """
    Generate makefile targets for a dataset, e.g. sgd, goa_human_rna

    Note any dataset can have multiple artifacts associated with it: gaf, gpad, gpi, ...
    """
    types = [a['type'] for a in alist]

    print("## --------------------")
    print("## {}".format(ds))
    print("## --------------------")
    if 'gaf' not in types and 'gpad' not in types:
        print("# Metadata incomplete\n")
        rule(all_files(ds), '','echo no metadata')
        return
    if ds == 'goa_pdb':
    # TODO move to another config file for 'skips'
        print("# Skipping\n")
        rule(all_files(ds), '','echo no metadata')
        return

    # If any item has the aggregate field, then we just want to pass it through and not run
    # all the targets
    ds_aggregate = any([("aggregates" in item) for item in alist])

    ds_targets = [targetdir(ds), gzip(filtered_gaf(ds)), gzip(filtered_gpad(ds)), gzip(gpi(ds)), gzip(ttl(ds))]
    ds_targets.append(owltools_gafcheck(ds))

    if ds_aggregate:
        ds_targets = [targetdir(ds), gzip(filtered_gaf(ds))]

    rule(all_files(ds), " ".join(ds_targets))

    rule(targetdir(ds),'',
         'mkdir -p $@')

    # for now we assume everything comes from a GAF
    if 'gaf' in types:
        [gaf] = [a for a in alist if a['type']=='gaf']
        url = gaf['source']
        # GAF from source
        rule(src_gaf(ds),'',
             'wget --no-check-certificate {url} -O $@.tmp && mv $@.tmp $@ && touch $@'.format(url=url))
    rule(filtered_gaf(ds),src_gaf(ds),
         'gzip -dc $< | ./util/new-filter-gaf.pl -m target/datasets-metadata.json -p '+ds+' -e $@.errors -r $@.report > $@.tmp && mv $@.tmp $@')
    rule(owltools_gafcheck(ds),src_gaf(ds),
         '$(OWLTOOLS_GAFCHECK)')
    rule(filtered_gpad(ds),filtered_gaf(ds),
         'owltools --gaf $< --write-gpad -o $@.tmp && mv $@.tmp $@')
    rule(gpi(ds),filtered_gaf(ds),
         'owltools --gaf $< --write-gpi -o $@.tmp && mv $@.tmp $@')
    rule(ttl(ds),"{} $(ONT_MERGED)".format(filtered_gaf(ds)),
         'MINERVA_CLI_MEMORY=16G minerva-cli.sh $(ONT_MERGED) --gaf $< --gaf-lego-individuals --skip-merge --format turtle -o $@.tmp && mv $@.tmp $@')


def targetdir(ds):
    return 'target/gafs/{ds}/'.format(ds=ds)
def all_files(ds):
    return 'all_'+ds
def src_gaf(ds):
    return '{dir}{ds}-src.gaf.gz'.format(dir=targetdir(ds),ds=ds)
def filtered_gaf(ds):
    return '{dir}{ds}-filtered.gaf'.format(dir=targetdir(ds),ds=ds)
def filtered_gpad(ds):
    return '{dir}{ds}-filtered.gpad'.format(dir=targetdir(ds),ds=ds)
def ttl(ds):
    return '{dir}{ds}.ttl'.format(dir=targetdir(ds),ds=ds)
def owltools_gafcheck(ds):
    return '{dir}{ds}-gafcheck'.format(dir=targetdir(ds),ds=ds)
def gpi(ds):
    return '{dir}{ds}.gpi'.format(dir=targetdir(ds),ds=ds)
def gzip(f):
    return '{}.gz'.format(f)

def rule(tgt,dep,ex='echo done'):
    s = "{tgt}: {dep}\n\t{ex}\n".format(tgt=tgt,dep=dep,ex=ex)
    print(s)

if __name__ == "__main__":
    main()
