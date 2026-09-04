# Photograph credits

Every photograph here came from Wikimedia Commons under an open licence, downloaded by
`src/tally/data/fetch_plates.py`. They stand in for the photographs a provider would take in
her own kitchen, so that Tally's vision step is tested against real food rather than drawings.

| File | Source | Licence | Author |
|---|---|---|---|
| `lunch_tray.jpg` | [School lunch tray MyPlate 20210810-FNS-UNC-0015.jpg](https://commons.wikimedia.org/wiki/File:School_lunch_tray_MyPlate_20210810-FNS-UNC-0015.jpg) | Public domain | U.S. Department of Agriculture |
| `chicken_rice_veg.jpg` | [Liat Portal for Foodie Disorder - Grilled chicken with rice and vegetables.jpg](https://commons.wikimedia.org/wiki/File:Liat_Portal_for_Foodie_Disorder_-_Grilled_chicken_with_rice_and_vegetables.jpg) | CC BY-SA 4.0 | HaJunkiyada |
| `school_lunch_fi.jpg` | [School lunch in ylästö school.jpg](https://commons.wikimedia.org/wiki/File:School_lunch_in_yl%C3%A4st%C3%B6_school.jpg) | CC0 | Jukajuha |
| `milk.jpg` | [Glass of Milk (33657535532).jpg](https://commons.wikimedia.org/wiki/File:Glass_of_Milk_(33657535532).jpg) | CC BY 2.0 | NIAID |
| `yogurt.jpg` | [Yoghurt in bowl 011715.jpg](https://commons.wikimedia.org/wiki/File:Yoghurt_in_bowl_011715.jpg) | CC BY-SA 4.0 | Susan Slater |
| `banana.jpg` | [Banana on whitebackground.jpg](https://commons.wikimedia.org/wiki/File:Banana_on_whitebackground.jpg) | CC BY-SA 4.0 | Filo gèn' |
| `oatmeal.jpg` | [Oatmeal porridge 1-minute with additional ingredients.jpg](https://commons.wikimedia.org/wiki/File:Oatmeal_porridge_1-minute_with_additional_ingredients.jpg) | CC BY-SA 4.0 | UserTwoSix |
| `crackers.jpg` | [Whole wheat Ritz Cracker (7571386026).jpg](https://commons.wikimedia.org/wiki/File:Whole_wheat_Ritz_Cracker_(7571386026).jpg) | CC BY 2.0 | Mark Taylor from Rockville, USA |
| `orange_slices.jpg` | [Blood orange slice.jpg](https://commons.wikimedia.org/wiki/File:Blood_orange_slice.jpg) | CC BY-SA 4.0 | Rhododendrites |
| `pear.jpg` | [Pears whole and in different stages of eating.jpg](https://commons.wikimedia.org/wiki/File:Pears_whole_and_in_different_stages_of_eating.jpg) | CC BY-SA 4.0 | OtuNwachinemere |
| `green_beans.jpg` | [Liat Portal for Foodie Disorder - Sautéed Green Beans with Onions.jpg](https://commons.wikimedia.org/wiki/File:Liat_Portal_for_Foodie_Disorder_-_Saut%C3%A9ed_Green_Beans_with_Onions.jpg) | CC BY-SA 4.0 | HaJunkiyada |

## Composed images

These two are composites of the photographs above, laid out side by side on a plain
surface by `src/tally/data/make_plates.py`. They stand in for the second photograph a
provider takes after adding a missing component. The credits above still apply.

| File | Composed from | Stands for |
|---|---|---|
| `oatmeal_with_milk.jpg` | `oatmeal.jpg`, `milk.jpg` | Breakfast after the missing milk was added. |
| `chicken_rice_veg_fixed.jpg` | `chicken_rice_veg.jpg`, `milk.jpg`, `orange_slices.jpg` | Lunch after the missing milk and fruit were added. |
