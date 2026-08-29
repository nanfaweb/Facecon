import sys

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

EYE_INPUT = 'eye_model_dataset.csv'
HAIR_INPUT = 'hair_model_dataset.csv'
EYE_OUTPUT = 'eye_model_final.csv'
HAIR_OUTPUT = 'hair_model_final.csv'

EYE_MAP = {
    'blue': 'Blue',
    'brown': 'Brown',
    'hazel': 'Intermediate',
    'green': 'Intermediate',
}

EYE_DROP = {'gray', 'amber'}

HAIR_MAP = {
    'blonde': 'Blond',
    'brown': 'Brown',
    'red': 'Red',
    'black': 'Black',
}

HAIR_DROP = {'gray', 'white'}


def print_counts(label, series):
    print(f'\n{label}')
    counts = series.value_counts(dropna=False).sort_index()
    for value, count in counts.items():
        print(f'  {value}: {count}')
    print(f'  Total: {len(series)}')


def relabel_eye(df):
    print('=' * 80)
    print('EYE COLOUR RELABELING')
    print('=' * 80)
    print_counts('Before:', df['eye_color'])

    dropped = df[df['eye_color'].isin(EYE_DROP)].copy()
    if not dropped.empty:
        print('\nDropped rows:')
        for _, row in dropped.iterrows():
            reason = 'not part of HIrisPlex-S 3-class scheme (n<3 combined)'
            print(f"  {row['participant_id']}: {row['eye_color']} -> {reason}")

    kept = df[~df['eye_color'].isin(EYE_DROP)].copy()
    kept['eye_color'] = kept['eye_color'].map(EYE_MAP)

    unmapped = kept[kept['eye_color'].isna()]
    if not unmapped.empty:
        values = sorted(unmapped['eye_color'].unique().tolist())
        raise ValueError(f'Unmapped eye colour values remain: {values}')

    print_counts('After:', kept['eye_color'])
    return kept


def relabel_hair(df):
    print('\n' + '=' * 80)
    print('HAIR COLOUR RELABELING')
    print('=' * 80)
    print_counts('Before:', df['hair_color'])

    dropped = df[df['hair_color'].isin(HAIR_DROP)].copy()
    if not dropped.empty:
        print('\nDropped rows:')
        for _, row in dropped.iterrows():
            reason = 'not part of HIrisPlex-S 4-class scheme (age-related/non-natural)'
            print(f"  {row['participant_id']}: {row['hair_color']} -> {reason}")

    kept = df[~df['hair_color'].isin(HAIR_DROP)].copy()
    unmapped_before_map = sorted(set(kept['hair_color'].unique()) - set(HAIR_MAP.keys()))
    if unmapped_before_map:
        raise ValueError(
            'Hair colour values require manual review (no mapping defined): '
            + ', '.join(unmapped_before_map)
        )

    kept['hair_color'] = kept['hair_color'].map(HAIR_MAP)

    unmapped = kept[kept['hair_color'].isna()]
    if not unmapped.empty:
        values = sorted(unmapped['hair_color'].unique().tolist())
        raise ValueError(f'Unmapped hair colour values remain: {values}')

    print_counts('After:', kept['hair_color'])
    return kept


def main():
    df_eye = pd.read_csv(EYE_INPUT)
    df_hair = pd.read_csv(HAIR_INPUT)

    eye_final = relabel_eye(df_eye)
    hair_final = relabel_hair(df_hair)

    eye_final.to_csv(EYE_OUTPUT, index=False)
    hair_final.to_csv(HAIR_OUTPUT, index=False)

    print('\n' + '=' * 80)
    print('OUTPUT FILES')
    print('=' * 80)
    print(f'  {EYE_OUTPUT}: N = {len(eye_final)}')
    print(f'  {HAIR_OUTPUT}: N = {len(hair_final)}')
    print('=' * 80)


if __name__ == '__main__':
    main()
