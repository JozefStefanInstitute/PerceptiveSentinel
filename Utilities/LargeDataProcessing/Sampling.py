from eolearn.core import EOPatch, FeatureType
import numpy as np
from sklearn.utils import resample
import random
import pandas as pd
import collections
import time


def sample_patches(path, no_patches, no_samples, class_feature, mask_feature, features, samples_per_class=None,
                   debug=False, seed=None, class_frequency=False):
    """
    :param path: Path to folder containing all patches, folders need to be named eopatch_{number: 0 to no_patches-1}
    :param no_patches: Total number of patches
    :param no_samples: Number of samples taken per patch
    :param class_feature: Name of feature that contains class number.
        The numbers in the array can be float or nan for no class
    :type class_feature: (FeatureType, string)
    :param mask_feature: Feature that defines the area from where samples are taken, if None the whole image is used
    :type mask_feature: (FeatureType, String) or None
    :param features: Features to include in returned dataset for each pixel sampled
    :type features: array of type [(FeatureType, string), ...]
    :param samples_per_class: Number of samples per class returned after balancing. If the number is higher than minimal
        number of samples for the smallest class then those numbers are upsampled by repetition.
        If the argument is None then number is set to the size of the number of samples of the smallest class
    :type samples_per_class: int or None
    :param debug: If set to True patch id and coordinates are included in returned DataFrame
    :param seed: Seed for random generator
    :return: pandas DataFrame with columns [class feature, features, patch_id, x coord, y coord].
        id,x and y are used for testing
    :param class_frequency: If set to True, the function also return dictionary of each class frequency before balancing
    :type class_frequency: boolean
    """
    if seed is not None:
        random.seed(seed)
    columns = [class_feature[1]] + [x[1] for x in features]
    if debug:
        columns = columns + ['patch_no', 'x', 'y']
    class_name = class_feature[1]
    sample_dict = []

    for patch_id in range(no_patches):
        eopatch = EOPatch.load('{}/eopatch_{}'.format(path, patch_id), lazy_loading=True)
        _, height, width, _ = eopatch.data['BANDS'].shape
        mask = eopatch[mask_feature[0]][mask_feature[1]].squeeze()
        no_samples = min(height * width, no_samples)
        subsample_id = []
        for h in range(height):
            for w in range(width):
                if mask is None or mask[h][w] == 1:
                    subsample_id.append((h, w))
        subsample_id = random.sample(subsample_id, min(no_samples, len(subsample_id)))

        for h, w in subsample_id:
            class_value = float(-1)
            if class_feature in eopatch.get_feature_list():
                val = float(eopatch[class_feature[0]][class_feature[1]][h][w])
                if not np.isnan(val):
                    class_value = val

            array_for_dict = [(class_name, class_value)] + [(f[1], float(eopatch[f[0]][f[1]][h][w])) for f in features]
            if debug:
                array_for_dict += [('patch_no', patch_id), ('x', w), ('y', h)]
            sample_dict.append(dict(array_for_dict))

    df = pd.DataFrame(sample_dict, columns=columns)
    df.dropna(axis=0, inplace=True)

    class_dictionary = collections.Counter(df[class_feature[1]])
    class_count = class_dictionary.most_common()
    least_common = class_count[-1][1]

    replace = False
    if samples_per_class is not None:
        least_common = samples_per_class
        replace = True
    df_downsampled = pd.DataFrame(columns=columns)
    names = [name[0] for name in class_count]
    dfs = [df[df[class_name] == x] for x in names]
    for d in dfs:
        nd = resample(d, replace=replace, n_samples=least_common, random_state=seed)
        df_downsampled = df_downsampled.append(nd)

    if class_frequency:
        return df_downsampled, class_dictionary
    return df_downsampled


# Example of usage
if __name__ == '__main__':
    # patches_path = 'E:/Data/PerceptiveSentinel/Slovenia'
    patches_path = '/home/beno/Documents/test/Slovenia'

    start_time = time.time()
    samples = sample_patches(path=patches_path,
                             no_patches=1061,
                             no_samples=500,
                             class_feature=(FeatureType.MASK_TIMELESS, 'LPIS_2017'),
                             mask_feature=(FeatureType.MASK_TIMELESS, 'EDGES_INV'),
                             features=[(FeatureType.DATA_TIMELESS, 'ARVI_max_mean_len'),
                                       (FeatureType.DATA_TIMELESS, 'EVI_min_val'),
                                       (FeatureType.DATA_TIMELESS, 'NDVI_min_val'),
                                       (FeatureType.DATA_TIMELESS, 'NDVI_sd_val'),
                                       (FeatureType.DATA_TIMELESS, 'SAVI_min_val'),
                                       (FeatureType.DATA_TIMELESS, 'SIPI_mean_val'),
                                       (FeatureType.DATA_TIMELESS, 'INCLINATION')
                                       ],
                             samples_per_class=500,
                             debug=True,
                             seed=None,
                             class_frequency=True)

    sample_time = time.time() - start_time
    filename = 'downsamplingOver'
    print(samples)
    result = 'Class sample size: {0}. Sampling time {1}'.format(
        int(samples['LPIS_2017'].size / pd.unique(samples['LPIS_2017']).size), sample_time)
    print(result)

    file = open('timing.txt', 'a')
    file.write('Sampling all 500 per patch, file: ' + filename + ' ' + result)
    file.close()

    samples.to_csv('D:/Samples/' + filename + '.csv')
