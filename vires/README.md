# VirES-Server - VirES for Swarm Server

The VirES-Server is a [Django](https://www.djangoproject.com/) app tailored to serve Swarm mission data by the [VirES for Swarm](https://vires.services) service.

The VirES-Server makes use of parts of the generic [EOxServer](https://github.com/EOxServer/eoxserver).

## Managment CLI

The content of the server is managed vi the Django `manage.py` command.

The available commands can be listed by

```
$ <instance>/manage.py --help
...
[vires]
    cached_product
    orbit_direction
    product
    product_collection
    product_type
...
```

These commands and their options are described in the following sections:

- [Product Types](#product-types)
- [Product Collections](#product-collections)
- [Data Products](#data-products)
- [Cached Products](#cached-products)
- [Orbit Direction Tables](#orbit-direction-tables)
- [Asynchronous Jobs](#asynchronous-jobs)


### Product Types

#### Product Type Import

The VirES-Server comes with a predefined set of product types for the supported Swarm and auxiliary products.
The default product types are loaded by the `import` command with the `--default` option:
```
$ <instance>/manage.py product_type import --default
```

New product types can be imported from their JSON definition, either from a file or from the standard input:
```
$ <instance>/manage.py product_type import -f new_product_types.json
$ <instance>/manage.py product_type import < new_product_types.json
```

Repeated product type import will replace (update) the existing product type definition.

Since the product types are linked with the product collections and they must be loaded before creating new collections.


#### Product Type Listing

The identifiers of the existing product types can be listed by the `list` command:
```
$ <instance>/manage.py product_type list
SW_AUX_IMF_2_
SW_EEFxTMS_2F
SW_EFIx_LP_1B
SW_FACxTMS_2F
SW_IBIxTMS_2F
SW_IPDxIRR_2F
SW_MAGx_HR_1B
SW_MAGx_LR_1B
SW_TECxTMS_2F
```


#### Product Type Export

The existing product type themselves can be exported by the `export` command. By default, the JSON data type definitions are printed to standard output although saving to a file is also possible:
```
$ <instance>/manage.py product_type export > product_types.json
$ <instance>/manage.py product_type export -f new_product_types.json
```

The export can be restricted to one or more product types passed as CLI arguments:
```
$ <instance>/manage.py product_type export SW_MAGx_HR_1B SW_MAGx_LR_1B | less -S
```


#### Product Type Removal

No longer needed product types can be removed from the system by the `remove` command:
```
$ <instance>/manage.py product_type remove SW_MAGx_HR_1B SW_MAGx_LR_1B
```

Removing of all product types requires the `--all` option to be used:
```
$ <instance>/manage.py product_type remove --all
```

Please note that the VirES server allows only removal of product types which are no longer attached to any product collection or registered product. If a product type is still in use its removal will be prevented.


### Product Collections

#### Product Collection Import

The registered products of the same product type are organized in collections. Multiple collections for same product type may exist, e.g., for different spacecrafts.

The VirES-Server comes with a predefined set of product collections for the supported Swarm and auxiliary products. The default product collections are loaded by the `import` command with the `--default` option:
```
$ <instance>/manage.py product_collection import --default
```

New definitions of the product collections and their metadata can be imported from a JSON file,
either from a file or from the standard input:
```
$ <instance>/manage.py product_collection import -f new_product_collections.json
$ <instance>/manage.py product_collection import < new_product_collections.json
```

Repeated product collection import will replace (update) the existing product collection.


#### Product Collection Listing

The identifiers of the existing product collections can be listed by the `list` command:
```
$ <instance>/manage.py product_collection list
SW_OPER_AUX_IMF_2_
SW_OPER_EEFATMS_2F
SW_OPER_EEFBTMS_2F
SW_OPER_EFIA_LP_1B
SW_OPER_EFIB_LP_1B
SW_OPER_EFIC_LP_1B
SW_OPER_FACATMS_2F
SW_OPER_FACBTMS_2F
SW_OPER_FACCTMS_2F
SW_OPER_FAC_TMS_2F
SW_OPER_IBIATMS_2F
SW_OPER_IBIBTMS_2F
SW_OPER_IBICTMS_2F
SW_OPER_IPDAIRR_2F
SW_OPER_IPDBIRR_2F
SW_OPER_IPDCIRR_2F
SW_OPER_MAGA_HR_1B
SW_OPER_MAGA_LR_1B
SW_OPER_MAGB_HR_1B
SW_OPER_MAGB_LR_1B
SW_OPER_MAGC_HR_1B
SW_OPER_MAGC_LR_1B
SW_OPER_TECATMS_2F
SW_OPER_TECBTMS_2F
SW_OPER_TECCTMS_2F
```

The listed collections can be selected by their product type:
```
$ <instance>/manage.py product_collection list -t SW_MAGx_HR_1B -t SW_MAGx_LR_1B
SW_OPER_MAGA_HR_1B
SW_OPER_MAGA_LR_1B
SW_OPER_MAGB_HR_1B
SW_OPER_MAGB_LR_1B
SW_OPER_MAGC_HR_1B
SW_OPER_MAGC_LR_1B
```


#### Product Collection Export

The existing product collections can be exported by the `export` command. By default, the JSON data collection definitions are printed to standard output although saving to a file is also possible:
```
$ <instance>/manage.py product_collection export > product_collections.json
$ <instance>/manage.py product_collection export -f new_product_collections.json
```

The export can be restricted to collections of one or more product types passed as the `-t` CLI option:
```
$ <instance>/manage.py product_collection export -t SW_MAGx_HR_1B -t SW_MAGx_LR_1B | less -S
```

The export can be also limited to one or more specific collections whose identifiers are passed as CLI arguments:
```
$ <instance>/manage.py product_collection export SW_OPER_MAGA_HR_1B SW_OPER_MAGC_HR_1B | less -S
```


#### Product Collection Removal

No longer needed product collections can be removed from the system by the `remove` command:
```
$ <instance>/manage.py product_collection remove SW_OPER_MAGA_HR_1B SW_OPER_MAGC_HR_1B
```

The removed collections can be restricted to one or more product types
```
$ <instance>/manage.py product_collection remove -t SW_MAGx_HR_1B -t SW_MAGx_LR_1B --all
```

Removing of all product collections matching the search criteria requires the `--all` option to be used:
```
$ <instance>/manage.py product_collection remove --all
```

Please note that the VirES server allows only removal of product collections which do not contain any registered product. If a product collection is still in use its removal will be prevented.


### Data Products

#### Product Registration

The product registration records the product metadata and data-file location.
One or more new data products are registered by the `register` command:
```
$ <instance>/manage.py product register -c SW_OPER_MAGA_LR_1B <fullpath>/SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409_MDR_MAG_LR.cdf ...
```

The command requires specification of the name of the collection (`-c` option) the products is linked to.

The product filenames are passed either as command line arguments or a text file with one filename per line (`-f` option) or via standard input (`-f -`):
```
$ <instance>/manage.py product register -c SW_OPER_MAGA_LR_1B -f product_list.txt
$ find /mnt/data -name SW_OPER_MAGA_LR_1B\*MDR_MAG_LR.cdf | <instance>/manage.py product register -c SW_OPER_MAGA_LR_1B -f -
```

The product identifier is automatically inferred from the product filename. Products in one collection must be unique. Registering the same product file in two different collections is possible but it is treated as two independent products.

By default, an attempts to register the same product in one collection again is **ignored**, this can be changed by the `--update` option:
```
$ <instance>/manage.py product register -c SW_OPER_MAGA_LR_1B --update -f product_list.txt
```

By default the registration does not allow time overlapping products to prevent accidental registration of different versions of the same product. The registration detects time-overlaps and **replaces** the old products by the new one. If this behavior is not desired (e.g., the registered products' times naturally overlap) use the `--ignore-overlaps` option:
```
$ <instance>/manage.py product register -c SW_OPER_MAGA_LR_1B --ignore-overlaps -f product_list.txt
```


#### Product Listing

The identifiers of the registered products can be listed by the `list` command:
```
$ <instance>/manage.py product list | less -S
```

The list it can be limited by product type (`-t` option), collection name (`-c` option) or acquisition times (`--after`, `--before`),  and first registration or update times (`--created-after`, `--created-before`, `--updated-after`, and `--updated-before`). The time constraints accept ISO-8601 timestamps or duration before the current time. E.g.:
```
$ <instance>/manage.py product list -t SW_MAGx_HR_1B -t SW_MAGx_LR_1B --after=2016-01-01 --before=2016-01-02
$ <instance>/manage.py product list -c SW_OPER_MAGA_HR_1B -c SW_OPER_MAGC_HR_1B --after=P31D
```

The list can be also constrained by a given list of product identifiers:
```
$ <instance>/manage.py product list <product-id> <product-id> ...
```

or product filenames (`-l` option):
```
$ <instance>/manage.py product list -l <filename> <filename> ...
```


#### Check Product Existence

To test if a product exists use the `exists` command:
```
$ <instance>/manage.py product exists SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409 && echo EXISTS || echo "DOES NOT EXIST"
INFO: SW_OPER_MAGA_LR_1B/SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409 exists
EXISTS

$ <instance>/manage.py product exists XYZ && echo EXISTS || echo "DOES NOT EXIST"
INFO: XYZ does not exist
DOES NOT EXIST
```

The result can be negated by the `--not` option:
```
$ <instance>/manage.py product exists --not SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409 && echo "DOES NOT EXIST" || echo EXISTS
INFO: SW_OPER_MAGA_LR_1B/SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409 exists
EXISTS

$ <instance>/manage.py product exists XYZ  || echo EXISTS && echo "DOES NOT EXIST"
INFO: XYZ does not exist
DOES NOT EXIST
```

The check accepts the same product selection options as the other product commands. E.g., the product type (`-t` option) or collection name (`-c` option):
```
$ <instance>/manage.py product exists -c SW_OPER_MAGA_LR_1B SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409 && echo EXISTS || echo "DOES NOT EXIST"
INFO: SW_OPER_MAGA_LR_1B/SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409 exists
EXISTS
```

The `-l` option allows checking products by filename rather than by the product identifier, i.e., it allows testing whether the given product file is registered or not:
```
$ <instance>/manage.py product exists -l <fullpath>/SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409_MDR_MAG_LR.cdf && echo EXISTS || echo "DOES NOT EXIST"
INFO: SW_OPER_MAGA_LR_1B/SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409 exists
EXISTS
```


#### Product Export

The full product records can be exported in JSON format by the `export` command:
```
$ <instance>/manage.py product export SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409_MDR_MAG_LR
[
  {
    "identifier": "SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409_MDR_MAG_LR",
    "beginTime": "2016-01-01T00:00:00+00:00",
    "endTime": "2016-01-01T23:59:59+00:00",
    "created": "2020-02-25T17:33:55.797654+00:00",
    "updated": "2020-02-25T17:33:55.797669+00:00",
    "collection": "SW_OPER_MAGA_LR_1B",
    "productType": "SW_MAGx_LR_1B",
    "metadata": {},
    "datasets": {
      "MDR_MAG_LR": {
        "location": "<fullpath>/SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409_MDR_MAG_LR.cdf"
      }
    }
  }
]
```

If no product identifier is specified all registered products are exported:
```
$ <instance>/manage.py product export > products_dump.json
```

The exported records can be limited by product type (`-t` option), collection name (`-c` option) or acquisition times (`--after`, `--before`),  and first registration or update times (`--created-after`, `--created-before`, `--updated-after`, and `--updated-before`). The time constraints accept ISO-8601 timestamps or duration before the current time. E.g.:
```
$ <instance>/manage.py product export -t SW_MAGx_HR_1B -t SW_MAGx_LR_1B --after=2016-01-01 --before=2016-01-02
$ <instance>/manage.py product export -c SW_OPER_MAGA_HR_1B -c SW_OPER_MAGC_HR_1B --after=P31D
```

The `-l` option allows selection of the exported product by the filename rather than by the product identifier:
```
$ <instance>/manage.py product export -l <filename> <filename> ...
```


#### Product Import

The JSON product definition exported by the export command can be imported to the same or another server instance by the `import` command:
```
$ <instance>/manage.py product import < products_dump.json
$ <instance>/manage.py product import -f products_dump.json
```

The import command is very powerful and significantly faster than the product registration command due to the skipped metadata extraction from the data files. This might, on the other hand, lead to undesired results and should be used with caution.

By default, the `import` command imports only new product records. To modify the existing records use the `--update` options.
```
$ <instance>/manage.py product import --update < products_dump.json
```

By default, the `import` command does not remove old product records. To fully synchronize the existing product records (i.e, also remove the records not present in the imported JSON definition) use the `--sync` options.
```
$ <instance>/manage.py product import --sync < products_dump.json
```

The imported records can be limited by product type (`-t` option), collection name (`-c` option) or acquisition times (`--after`, `--before`), and first registration or update times (`--created-after`, `--created-before`, `--updated-after`, and `--updated-before`). The time constraints accept ISO-8601 timestamps or duration before the current time. E.g.:
```
$ <instance>/manage.py product import -t SW_MAGx_HR_1B -t SW_MAGx_LR_1B --after=2016-01-01 --before=2016-01-02 < products_dump.json
$ <instance>/manage.py product import -c SW_OPER_MAGA_HR_1B -c SW_OPER_MAGC_HR_1B --after=P31D < products_dump.json
```

This selection can be combined with the `--sync` and `--update` options to limit, e.g., the synchronization to one or more selected collections:
```
$ <instance>/manage.py product import -c SW_OPER_MAGA_HR_1B --sync --update < products_dump.json
```


#### Product De-registration

The product de-registration (`deregister` command) removes products records from the server:
```
$ <instance>/manage.py product deregister SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409_MDR_MAG_LR
```

To de-register all products matching the filter criteria the `--all` option must be used:
```
$ <instance>/manage.py product deregister --all
```

The de-registered products be limited their product type (`-t` option), collection name (`-c` option) or acquisition times (`--after`, `--before`),  and first registration or update times (`--created-after`, `--created-before`, `--updated-after`, and `--updated-before`). The time constraints accept ISO-8601 timestamps or duration before the current time. E.g.:
```
$ <instance>/manage.py product deregister --all -t SW_MAGx_HR_1B -t SW_MAGx_LR_1B --after=2016-01-01 --before=2016-01-02
$ <instance>/manage.py product deregister --all -c SW_OPER_MAGA_HR_1B -c SW_OPER_MAGC_HR_1B --after=P31D
```

The `-l` option allows selection of the de-registrated products by the filename rather than by their identifier:
```
$ <instance>/manage.py product deregister -l <filename> <filename> ...
```


#### Detection and De-registration of Invalid Products

It may happen that the data files registered products no longer exist, i.e., the data files were removed while the VirES server records still exist.

To detect and de-register only the invalid products use the `--invalid-only` option with the `deregister` command.
```
$ <instance>/manage.py product deregister --invalid-only
```

The `--invalid-only` option is also accepted by the `list` and `export` commands and thus it can be used to detect and inspect invalid product records:
```
$ <instance>/manage.py product list --invalid-only
$ <instance>/manage.py product export --invalid-only
```

The `--invalid-only` command is also accepted by the `import` command, though, in this case it is only applied when the products are removed with the `--sync` option:
```
$ <instance>/manage.py product import -t SW_MAGx_LR_1B --sync --invalid-only < products_dump.json
```


### Cached Products

The so called *cached products* are special datasets which are read from one source file(s) and **copied** into the server. The copying may involve change of the data format or merging of multiple input files into one.

There is a predefined (hard-coded) set of cached products listed in the following table:

| Type | Nr. of Inputs | Description | Reference/Source |
|:---|:---:|:---|:---|
| `AUXAORBCNT` | 1 | Swarm A orbit counter file |[[Swarm Orbit Counter Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_Orbit_Counter_Specifications_ORBCNT)]|
| `AUXBORBCNT` | 1 | Swarm B orbit counter file |[[Swarm Orbit Counter Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_Orbit_Counter_Specifications_ORBCNT)]|
| `AUXCORBCNT` | 1 | Swarm C orbit counter file |[[Swarm Orbit Counter Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_Orbit_Counter_Specifications_ORBCNT)]|
| `AUX_F10_2_` | 1 | Swarm `AUX_F10_2_` product |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)]|
| `GFZ_AUX_DST` | 1 | Dst index downloaded from this |[[GFZ FTP server](ftp://ftp.gfz-potsdam.de/pub/incoming/champ_payload/Nils/Dst_MJD_1998.dat)]|
| `GFZ_AUX_KP` | 1 | Kp10 index downloaded from this |[[GFZ FTP server](tp://ftp.gfz-potsdam.de/pub/incoming/champ_payload/Nils/Kp_MJD_1998_QL.dat)]|
| `MCO_SHA_2C` | 1 | Swarm `MCO_SHA_2C` core field model |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)]|
| `MCO_SHA_2D` | 1 | Swarm `MCO_SHA_2D` core field model |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)]|
| `MCO_SHA_2F` | 1 | Swarm `MCO_SHA_2F` core field model |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)]|
| `MCO_SHA_2X` | 1 | Swarm `MCO_SHA_2X` (CHAOS-Core) core field model |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)] |
| `MIO_SHA_2C` | 1 | Swarm `MIO_SHA_2C` ionospheric variation model |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)] |
| `MIO_SHA_2D` | 1 | Swarm `MIO_SHA_2D` ionospheric variation model |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)] |
| `MLI_SHA_2C` | 1 | Swarm `MLI_SHA_2C` crustal field model |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)] |
| `MLI_SHA_2D` | 1 | Swarm `MLI_SHA_2D` crustal field model |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)] |
| `MLI_SHA_2E` | 1 | Swarm `MLI_SHA_2E` crustal field model |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)] |
| `MMA_CHAOS_` | N | CHAOS magnetospheric field model |[[DTU web server](http://www.spacecenter.dk/files/magnetic-models/RC/MMA/)] |
| `MMA_SHA_2C` | 1 | Swarm `MMA_SHA_2C` magnetospheric field model |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)] |
| `MMA_SHA_2F` | N | Swarm `MMA_SHA_2F` magnetospheric field model |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)] |


#### Cached Product Update

A cached product is updated by the `update` command:
```
$ <instance>/manage.py cached_product update <type> <input-file> ...
```
The available cached product types are described in the table above.

The update of the `MMA_SHA_2F` and `MMA_CHAOS_` types accepts multiple input model files. The command selects the applicable ones, sorts them in the right temporal order and merges them together into one dataset. In case of gaps between the models, the latest contiguous part is picked.


#### Cached Product Details

To get details about the state of the cached products (last update and source products identifiers) in JSON format use the `dump` command:
```
$ <instance>/manage.py cached_product update
[
  {
    "identifier": "AUX_F10_2_",
    "updated": "2020-02-27T09:53:13Z",
      ...
   }
]
```

By default the `dump` command lists all cached products but the output can be restricted by the type, e.g.:
```
$ <instance>/manage.py cached_product dump GFZ_AUX_KP GFZ_AUX_DST
[
  {
    "identifier": "GFZ_AUX_KP",
    "updated": "2020-02-27T09:53:11Z",
    "location": "<cache-path>/aux_kp.cdf",
    "sources": [
      "SW_OPER_AUX_KP__2__19980101T013000_20200212T133000_0001"
    ]
  },
  {
    "identifier": "GFZ_AUX_DST",
    "updated": "2020-02-27T09:53:07Z",
    "location": "<cache-path>/aux_dst.cdf",
    "sources": [
      "SW_OPER_AUX_DST_2__19980101T003000_20200211T233000_0001"
    ]
  }
]
```


### Orbit Direction Tables

The orbit direction tables are a special case of the cached products. These tables contain the times of the starts of the ascending and descending passes in geographic and magnetic (Quasi-Dipole) coordinates for each Swarm spacecraft. These tables are used to quickly look up orbit direction for the measurements.

The orbit direction tables are extracted from the positions contained in the `SW_MAGx_LR_1B` products. By default, they are extracted during the registration of new products. This section describe how to fix the tables for the already registered products.

The orbit directions can be updated for one or more individual `SW_MAGx_LR_1B` products by the `update` command, e.g.,:
```
$ <instance>/manage.py orbit_direction update SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409_MDR_MAG_LR
```

The command checks if the product has been already processed. If not, the orbit direction information is extracted from the requested products. Already processed products are skipped.

To synchronize the orbit direction for the whole collection use the `sycn` command with the names of collections to synchronize:
```
$ <instance>/manage.py orbit_direction sync SW_OPER_MAGA_LR_1B SW_OPER_MAGC_LR_1B
```

The `sync` command without any collection name synchronizes the orbit directions for all spacecrafts:
```
$ <instance>/manage.py orbit_direction sync
```

The `sycn` command checks the available products and if not yet processed the tables are updated.

If necessary, the orbit direction tables can be rebuilt from scratch by the `rebuild` command either for one or more specific input collections:
```
$ <instance>/manage.py orbit_direction rebuild SW_OPER_MAGA_LR_1B SW_OPER_MAGC_LR_1B
```

or for all spacecrafts if no collection is specified:
```
$ <instance>/manage.py orbit_direction rebuild
```


### Asynchronous Jobs

Data downloads in VirES are performed asynchronously, i.e., the download requests are passed to an asynchronous backend (daemon) which puts them as *jobs* in a FIFO queue and processes them gradually by the employed pool of worker processes.

The asynchronous backend keeps track of the jobs itself but, in order to track additional information about the asynchronous jobs, the VirES server holds additional DB record for each job.


#### Listing Jobs

Identifiers of all asynchronous jobs can be listed by the `list` command:
```
$ <instance>/manage.py job list
```

The list can can be constrained by additional selection criteria, e.g., owner, status, completion time, etc.:
```
$ <instance>/manage.py job list -u vagrant -s SUCCEEDED -s FAILED --ended-after P1D
```

For the complete list of the selection options see the command help invoked by the `--help` option:
```
$ <instance>/manage.py job list --help
```


#### Listing Loose Jobs

The loose jobs are invalid job DB records for which no actual asynchronous job exists. The loose jobs should never be present on a production system, though, they might be encountered during development and testing.

Identifiers of the loose asynchronous jobs can be listed by the `list` command with the `--loose` option:
```
$ <instance>/manage.py job list --loose
```


#### Listing Dangling Jobs

The dangling jobs are existing asynchronous jobs for which no DB record exists. The dangling jobs should never be present on a production system, though, they might be encountered during development and testing.

Identifiers of the dangling asynchronous jobs can be listed by the `dangling_job` `list` command:
```
$ <instance>/manage.py dangling_job list
```

For the complete list of the selection options see the command help invoked by the `--help` option:
```
$ <instance>/manage.py dangling_job list --help
```


#### Getting Jobs' Details

Details of all asynchronous jobs can be exported by the `info` command in CSV format:
```
$ <instance>/manage.py job info | column -t -s , | less -S
```

Just like the list command, the info output can be constrained by additional selection criteria, e.g., owner, status, completion time, etc.:
```
$ <instance>/manage.py job info -u vagrant -s SUCCEEDED -s FAILED --ended-after P1D
```

For the complete list of the selection options see the command help invoked by the `--help` option:
```
$ <instance>/manage.py job info --help
```


#### Getting Loose Jobs' Details

Details of the loose asynchronous jobs can be listed by the `info` command with the `--loose` option:
```
$ <instance>/manage.py job info --loose | column -t -s , | less -S
```


#### Getting Dangling Jobs' Details

Details of the dangling asynchronous jobs can be printed by the `dangling_job` `info` command:
```
$ <instance>/manage.py dangling_job info | column -t -s , | less -S
```

For the complete list of the selection options see the command help invoked by the `--help` option:
```
$ <instance>/manage.py dangling_job info --help
```


#### Dumping Jobs' Details in JSON Format

Alternatively, details of all asynchronous jobs can be dumped by the `dump` command in JSON format:
```
$ <instance>/manage.py dump info
```

Just like the list command, the output can be constrained by additional selection criteria, e.g., owner, status, completion time, etc.:
```
$ <instance>/manage.py dump info -u vagrant -s SUCCEEDED -s FAILED --ended-after P1D
```

For the complete list of the selection options see the command help invoked by the `--help` option:
```
$ <instance>/manage.py dump info --help
```


#### Dumping Loose Jobs' Details in JSON Format

Details of the loose asynchronous jobs can be dumped as JSON by the `dump` command with the `--loose` option:
```
$ <instance>/manage.py job dump --loose



#### Dumping Dangling Jobs' Details in JSON Format

Details of the dangling asynchronous jobs can be dumped by the `dangling_job` `dump` command:
```
$ <instance>/manage.py dangling_job dump
```

For the complete list of the selection options see the command help invoked by the `--help` option:
```
$ <instance>/manage.py dangling_job dump --help
```


#### Removing Jobs

Selected asynchronous jobs can be removed by the `remove` command:
```
$ <instance>/manage.py job remove <job-id> <job-id> ...
```

Alternatively, all jobs matched by the selection criteria can be removed with the `--all` option:
```
$ <instance>/manage.py job remove --all
```

Just like the list command, the info output can can be constrained by additional selection criteria, e.g., owner, status, completion time, etc.:
```
$ <instance>/manage.py job remove --all -u vagrant -s SUCCEEDED -s FAILED --ended-after P1D
```

For the complete list of the selection options see the command help invoked by the `--help` option:
```
$ <instance>/manage.py job remove --help
```


#### Removing Loose Jobs

The loose asynchronous jobs can be removed by the `remove` command with the `--loose` option:
```
$ <instance>/manage.py job remove --loose --all
```


#### Removing Dangling Jobs

Identifiers of the dangling asynchronous jobs can be removed by the `dangling_job` `remove` command:
```
$ <instance>/manage.py dangling_job remove
```

For the complete list of the selection options see the command help invoked by the `--help` option:
```
$ <instance>/manage.py dangling_job remove --help
```
