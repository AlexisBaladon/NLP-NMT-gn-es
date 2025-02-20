import argparse

from src.pipelines import train_pipeline
from src.utils import parsing
from src.logger import logging
from src.config import command_config as command, ingestion_config as ingestion, hyperparameter_tuning_config, finetuning_config
from src.config.config import load_config_variables, FLAG_SEPARATOR

def parse_args():
    parser = argparse.ArgumentParser()

    # Global
    parser.add_argument('--flags', type=str, required=True)
    parser.add_argument('--seed', type=int, required=False, default=1234, help='Seed to make results reproducible')

    # Pipeline steps
    parser.add_argument('--ingest', action='store_true', required=False, default=False)
    parser.add_argument('--train', action='store_true', required=False, default=False)
    parser.add_argument('--finetuning', action='store_true', required=False, default=None)

    # Ingestion
    parser.add_argument('--ingest-augmented-data', action='store_true', required=False, default=False)

    # Finetuning
    parser.add_argument('--finetuning-epochs', type=str, required=False, default=None, help='Whitespace separated list of training sets')
    parser.add_argument('--finetuning-full-sets', type=str, required=False, default=None, help='Whitespace separated list of train + augmented sets')
    parser.add_argument('--finetuning-augmented-sets', type=str, required=False, default=None, help='Whitespace separated list of augmented sets')
    parser.add_argument('--finetuning-cache-template-dir', type=str, required=False, default=None, help='Cache template dir for models')

    # Training
    parser.add_argument('--train-sets', type=str, required=False, default=None, help='Whitespace separated list of training sets')
    parser.add_argument('--command-path', type=str, required=True, help='Path to the model executable')
    parser.add_argument('--validate-each-epochs', type=int, required=False, default=None, help='Number of epochs between validations')
    parser.add_argument('--validation-metrics', type=str, required=False, default=None, help='Whitespace separated list of metrics to use for validation')
    parser.add_argument('--save-checkpoints', action='store_true', required=False, default=False, help='Save a copy of the model after each validation')
    parser.add_argument('--not-delete-model-after', action='store_true', required=False, default=False, help='Do not delete the model after training')

    # Hyperparameter tuning
    parser.add_argument('--run-id', type=str, required=False, default='default', help='Run id to distinguish within different runs checkpoints')
    parser.add_argument('--hyperparameter-tuning', action='store_true', required=False, default=False, help='Run hyperparameter tuning')
    parser.add_argument('--tuning-grid-files', type=str, required=False, default=None, help='Whitespace separated list of files with a grid of configurations')
    parser.add_argument('--tuning-params-files', type=str, required=False, default=None, help='Whitespace separated list of files with only one configuration')
    parser.add_argument('--from-flags', type=int, required=False, default=None, help='Loads from flag combination number N from all configs from the provided configs/grids')
    parser.add_argument('--to-flags', type=int, required=False, default=None, help='Stops after flag combination number N from all configs from the provided configs/grids')
    parser.add_argument('--tuning-strategy', type=str, required=False, default='gridsearch', help="Tuning strategy to use. Can be 'gridsearch' or 'randomsearch'")
    parser.add_argument('--max-iters', type=int, required=False, default=None, help='Maximum number of iterations to run hyperparameter tuning')

    return vars(parser.parse_args())

if __name__ == '__main__':
    args = parse_args()

    # Global
    flags = args.get('flags')
    seed = args.get('seed')

    # Training
    command_path = args.get('command_path')
    validate_each_epochs = args.get('validate_each_epochs')
    validation_metrics = args.get('validation_metrics')
    save_checkpoints = args.get('save_checkpoints')
    not_delete_model_after = args.get('not_delete_model_after')

    # Steps
    ingest = args.get('ingest')
    finetune = args.get('finetuning')
    train = args.get('train')

    # Ingestion
    ingest_augmented_data = args.get('ingest_augmented_data')

    # Finetuning
    finetuning_epochs = args.get('finetuning_epochs')
    finetuning_full_sets = args.get('finetuning_full_sets')
    finetuning_augmented_sets = args.get('finetuning_augmented_sets')
    finetuning_cache_template_dir = args.get('finetuning_cache_template_dir')

    # Hyperparameter tuning
    run_id = args.get('run_id')
    hyperparameter_tuning = args.get('hyperparameter_tuning')
    tuning_grid_files = args.get('tuning_grid_files')
    tuning_params_files = args.get('tuning_params_files')
    from_flags = args.get('from_flags')
    to_flags = args.get('to_flags')
    tuning_strategy = args.get('tuning_strategy')
    max_iters = args.get('max_iters')
    
    config_variables = load_config_variables()
    flag_separator = config_variables.get(FLAG_SEPARATOR, ' ')
    command_config, ingestion_config, tuning_config, finetune_config = 4*[None]

    flags = parsing.parse_flags(flags, flag_separator=flag_separator)
    train_dirs = flags.get('train-sets', [])
    val_dirs = flags.get('valid-sets', [])
    logging.info('Running with flags {}'.format(flags))

    if ingest:
        vocab_dirs = flags.get('vocabs', [])
        ingestion_config = ingestion.get_data_ingestion_config(config_variables, 
                                                               train_dirs, 
                                                               val_dirs, 
                                                               vocab_dirs, 
                                                               ingest_augmented_data, 
                                                               persist_each=1000)
        logging.info('Ingesting data with config {}'.format(ingestion_config))

    if train:
        validation_metrics = validation_metrics.split(' ') if validation_metrics  else None
        tuning_grid_files = tuning_grid_files.split(' ') if tuning_grid_files else []
        tuning_params_files = tuning_params_files.split(' ') if tuning_params_files else []
        command_config = command.get_command_config(command_path, flags, 
                                                    validate_each_epochs=validate_each_epochs, 
                                                    validation_metrics=validation_metrics, 
                                                    save_checkpoints=save_checkpoints, 
                                                    not_delete_model_after=not_delete_model_after,
                                                    run_id=run_id)
        logging.info('Training model with config {}'.format(command_config))

        if finetune:
            finetuning_full_sets = finetuning_full_sets.split(' ') if finetuning_full_sets else None
            finetuning_augmented_sets = finetuning_augmented_sets.split(' ') if finetuning_augmented_sets else []
            finetune_config = finetuning_config.get_finetuning_config(finetuning_epochs, 
                                                                      finetuning_augmented_sets, 
                                                                      finetuning_full_sets,
                                                                      cache_dir_template=finetuning_cache_template_dir)

        if hyperparameter_tuning:
            tuning_config = hyperparameter_tuning_config.get_hyperparameter_tuning_config(run_id=run_id,
                                                                                          tuning_grid_files=tuning_grid_files, 
                                                                                          tuning_params_files=tuning_params_files,
                                                                                          from_flags=from_flags, 
                                                                                          to_flags=to_flags,
                                                                                          tuning_strategy=tuning_strategy,
                                                                                          seed=seed,
                                                                                          max_iters=max_iters)
            logging.info('Hyperparameter tuning with config {}'.format(tuning_config))

    try:
        train_pipeline.train(command_config=command_config, 
                             data_ingestion_config=ingestion_config,
                             hyperparameter_tuning_config=tuning_config,
                             finetuning_config=finetune_config)
    except Exception as e:
        logging.error('Error while training with config {} and {}'.format(command_config, 
                                                                          ingestion_config))
        raise e