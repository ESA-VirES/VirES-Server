# VirES-Server - VirES for Swarm Server

The VirES-Server is a a [Django](https://www.djangoproject.com/) app tailored to serve Swarm mission data by the [VirES for Swarm](https://vires.services) service.

The VirES server makes use of parts of the generic [EOxServer](https://github.com/EOxServer/eoxserver).

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

### Product Types

#### Product Type Import
The VirES-Server comes with a predefined set of product types of the supported products.
The default product types are loaded by the `import` command:

```
$ <instance>/manage.py product_type import
```

New product types can be imported from their JSON definition, either from a file or from the standard input:

```
$ <instance>/manage.py product_type import -f new_product_types.json
$ <instance>/manage.py product_type import < new_product_types.json
```

Repeated product type import will replace (update) the existing product type definition.

Since the product types are linked with the product collections and the actual products they must be loaded first.


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

The VirES-Server comes with a predefined set of product collections for the supported Swarm products. The default definitions are loaded by the `import` command:

```
$ <instance>/manage.py product_collection import
```

New definitions of the product collections and their metadata can imported from a JSON file,
either from a file or from the standard input:

```
$ <instance>/manage.py product_collection import -f new_product_collections.json
$ <instance>/manage.py product_collection import < new_product_collections.json
```

Repeated product collection import will replace (update) the existing product collections.

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

The listed collections can be listed by their product type:

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
The existing product collections can be exported by the `export` command. By default, the JSON data type definitions are printed to standard output although saving to a file is also possible:

```
$ <instance>/manage.py product_collection export > product_collections.json
$ <instance>/manage.py product_collection export -f new_product_collections.json
```

The export can be restricted to collections of one or more product types passed as the `-t` CLI option:

```
$ <instance>/manage.py product_collection export -t SW_MAGx_HR_1B -t SW_MAGx_LR_1B | less -S
```

Or the export can be restricted to one or more specific collections passed as CLI arguments:

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

Please note that the VirES server allows only removal of product collections which no longer contain any registered product. If a product collection is still in use its removal will be prevented.

### Data Products

#### Product Registration

The products registration records the data-file locations and extracts their metadata.
One or more new data products are registered in the server by the `register` command:

```
$ <instance>/manage.py product register -c SW_OPER_MAGA_LR_1B <fullpath>/SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409_MDR_MAG_LR.cdf ...
```

The command requires specification of the name of the collection (`-c` option) to which the products linked.
The product filenames are passed either as command line arguments or they can be passed in a file (`-f` option) or via standard input (`-f -`)

```
$ <instance>/manage.py product register -c SW_OPER_MAGA_LR_1B -f product_list.txt
$ find /mnt/data -name SW_OPER_MAGA_LR_1B\*MDR_MAG_LR.cdf | <instance>/manage.py product register -c SW_OPER_MAGA_LR_1B -f -
```

The product identifier is inferred from the product filename. Products in one collection must be unique. Registering the same product file in two different collections is possible but it is treated as two independent products.

By default, an attempts to register the same product in one collection again is **ignored**, this can be changed by setting the `--conflict` option to `UPDATE` which updates the original product record:

```
$ <instance>/manage.py product register -c SW_OPER_MAGA_LR_1B --conflict=UPDATE -f product_list.txt
```

By default the registration does not allow time overlapping products to prevent accidental registration of different versions of the same product. The registration detects time-overlaps and **replaces** the old products by the new one. If this behavior is not desired (e.g., the registered products' times naturally overlap) set the `--overlap` option to `IGNORE`:

```
$ <instance>/manage.py product register -c SW_OPER_MAGA_LR_1B --overlap=IGNORE -f product_list.txt
```

#### Product Listing

The identifiers of the registered products can be listed by the `list` command:

```
$ <instance>/manage.py product list | less -S
```

The list may be quite long and it can be limited by the product type (`-t` option), collection name (`-c` option) or acquisition times (`--after`, `--before`, `--created-after`, `--created-before`, `--updated-after`, and `--updated-before` options accepting ISO-8601 timestamps or duration relative to the current time), e.g.:


```
$ <instance>/manage.py product list -t SW_MAGx_HR_1B -t SW_MAGx_LR_1B --after=2016-01-01 --before=2016-01-02
$ <instance>/manage.py product list -c SW_OPER_MAGA_HR_1B -c SW_OPER_MAGC_HR_1B --after=-P31D
```

#### Product Export

More details on the individual products can be exported in JSON format by the `export` command:

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
$ <instance>/manage.py product product exported > products_dump.json
```

The product output can be limited by the product type (`-t` option), collection name (`-c` option) or acquisition, creation and last update times (`--after`, `--before`, `--created-after`, `--created-before`, `--updated-after`, and `--updated-before` options accepting ISO-8601 timestamps or duration relative to the current time), e.g.:

```
$ <instance>/manage.py product list -t SW_MAGx_HR_1B -t SW_MAGx_LR_1B --after=2016-01-01 --before=2016-01-02
$ <instance>/manage.py product list -c SW_OPER_MAGA_HR_1B -c SW_OPER_MAGC_HR_1B --after=-P31D
```

#### Product Import

The JSON product definition exported by the export command can be imported to the same or another server instance by the `import` command:
```
$ <instance>/manage.py product product import < products_dump.json
$ <instance>/manage.py product product import -f products_dump.json
```
The import command is significantly faster then the regular product registration command, though, it might produce invalid product records and should be used with caution.

#### Product De-registration

The product de-registration (`deregister` command) removes products records from the server:
```
$ <instance>/manage.py product deregister SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409_MDR_MAG_LR

```

To de-register all products matching the filter criteria the `--all` option must be used:
```
$ <instance>/manage.py product deregister --all

```

The products to be de-registered can be constrained by the product type (`-t` option), collection name (`-c` option) or acquisition times (`--after`, `--before`, `--created-after`, `--created-before`, `--updated-after`, and `--updated-before` options accepting ISO-8601 timestamps or duration relative to the current time), e.g.:


```
$ <instance>/manage.py product deregister --all -t SW_MAGx_HR_1B -t SW_MAGx_LR_1B --after=2016-01-01 --before=2016-01-02
$ <instance>/manage.py product deregister --all -c SW_OPER_MAGA_HR_1B -c SW_OPER_MAGC_HR_1B --after=-P31D
```

#### Detection and De-registration of Invalid Products

It may happen that the registered products no longer exist in the file-system, i.e., the data-files were removed while the VirES server records still exist.

To detect and de-register only the invalid products use the `--invalid-only` option with the `deregister` command.

```
$ <instance>/manage.py product deregister --invalid-only
```

The `--invalid-only` option is also accepted by the `list` and `dump` commands and thus it can be used to detect and inspect invalid product records:

```
$ <instance>/manage.py product list --invalid-only
$ <instance>/manage.py product dump --invalid-only
```

### Cached Products

The so called *cached products* are special datasets which are hold by the server. In this cases the data is read from one file(s) and copied into the server. The copying may involve change of the data format or merging of multiple input files into one.

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
| `MMA_CHAOS_` | N | CHAOS magnetospheric field model |[[DTU web server](http://www.spacecenter.dk/files/magnetic-models/RC/MMA/)] |
| `MMA_SHA_2C` | 1 | Swarm `MMA_SHA_2C` magnetospheric field model |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)] |
| `MMA_SHA_2F` | N | Swarm `MMA_SHA_2F` magnetospheric field model |[[Swarm L2 Product Spec.](https://earth.esa.int/documents/10174/1514862/Swarm_L2_Product_Specification)] |

#### Cached Product Update

A cached product is updated by the `update` command:
```
$ <instance>/manage.py cached_product update <type> <input-file> ...
```
The available cached product types are described in the table above.

The update of the `MMA_SHA_2F` and `MMA_CHAOS_` types accepts multiple input model files. The command selects the applicable ones, sorts them in the right temporal order and merges them together into one product. In case of gaps between the models, the latest contiguous part is picked.

#### Cached Product Details

To get details about the state of the cached products (last update and source products identifiers) in JSON format use `dump` command:

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

The orbit direction tables are a special case of the cached products. These tables contain the times of the starts of the ascending and descending passes in geographic and magnetic (Quasi-Dipole) coordinate frames for each Swarm spacecraft. These tables are used to quickly look up orbit direction for the measurements.

The orbit direction tables are extracted from the positions contained in the `SW_MAGx_LR_1B` products. By default, they are extracted during the registration of new products. This section describe how to fix the tables for the already registered products.

The orbit direction can be updated for one or more individual `SW_MAGx_LR_1B` products by the `update` command, e.g.,:
```
$ <instance>/manage.py orbit_direction update SW_OPER_MAGA_LR_1B_20160101T000000_20160101T235959_0409_MDR_MAG_LR
```
The command checks if the product has been already processed. If not, the orbit direction information is extracted from the requested products. Already processed products are skipped.

To synchronize the orbit direction for the whole collection use `sycn` command with the names of collections to synchronize:
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