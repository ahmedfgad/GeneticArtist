import glob
import pygad
import cv2 as cv
import numpy as np
import image_ops
from pathos.multiprocessing import Pool
import genetic_artist_config

# Why pathos: https://stackoverflow.com/a/21345308


class GeneticArtistException(Exception):
    """Exception raised for errors from a GeneticArtist object

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message=''):
        self.message = f'Genetic Artist error: {message}'
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}'


class NonMatchingCanvasSize(GeneticArtistException):
    """Exception raised when the target image and the canvas do not have the same size"""

    def __init__(self):
        super().__init__('The canvas and the target image must be the same size')


class EmptyStrokeImgList(GeneticArtistException):
    """Exception raised when the provided stroke image directory has no valid images

    Attributes:
        stroke_img_dir_path -- path to the stroke image directory
    """

    def __init__(self, stroke_img_dir_path: str):
        super().__init__(f'No stroke images were found in {stroke_img_dir_path}')


class ImageNotFoundError(GeneticArtistException):
    """Exception raised when an image is not found

    Attributes:
        file_path -- path to the missing image
    """

    def __init__(self, file_path: str):
        super().__init__(f'Image \'{file_path}\' not found')


class OutputImageError(GeneticArtistException):
    """Exception raised when outputing an image as a file fails

    Attributes:
        output_path -- output path of the image
    """

    def __init__(self, output_path: str):
        super().__init__(f'Failed to write output to \'{output_path}\'')


class ConfigFileNotFoundError(GeneticArtistException):
    """Exception raised when the config file is not found

    Attributes:
        file_path -- path to the missing config file
    """

    def __init__(self, config_path: str):
        super().__init__(f'Config file \'{config_path}\' not found')


class ConfigFileError(GeneticArtistException):
    """Exception raised when the config file contains errors

    Attributes:
        error -- error description
    """

    def __init__(self, error: str):
        super().__init__(f'Config file error: {error}')


class PooledGA(pygad.GA):
    #Laszlo Fazekas, How Genetic Algorithms Can Compete with Gradient Descent and Backprop, Hackernoon
    #https://hackernoon.com/how-genetic-algorithms-can-compete-with-gradient-descent-and-backprop-9m9t33bq, March 2021
    _processes: int

    def __init__(self, processes, **kwargs):
        super().__init__(**kwargs)
        self._processes = processes

    def fitness_wrapper(self, solution):
        return self.fitness_func(solution, 0)

    def cal_pop_fitness(self):
        with Pool(processes=self._processes) as pool:
            pop_fitness = pool.map(self.fitness_wrapper, self.population)
            pop_fitness = np.array(pop_fitness)
            return pop_fitness


class GeneticArtist:
    def __init__(self, target_img_path: str, 
                 stroke_img_dir_path: str, 
                 config: genetic_artist_config.Configuration, 
                 canvas_img_path: str = None):
        # Define instance variables
        self._target_img: np.array
        self._canvas_img: np.array
        self._stroke_img_list: list[np.array] = []

        # Load target image
        self._target_img = cv.imread(target_img_path)
        if self._target_img is None:
            raise ImageNotFoundError(target_img_path)

        # Store stroke images
        stroke_img_dir_ls = glob.glob(f'{stroke_img_dir_path}/*')
        for file in stroke_img_dir_ls:
            read_img = cv.imread(file, cv.IMREAD_GRAYSCALE)
            if read_img is not None:
                self._stroke_img_list.append(read_img)
        if len(self._stroke_img_list) == 0:
            raise EmptyStrokeImgList(stroke_img_dir_path)

        # Store canvas image if specified or create blank canvas image otherwise
        if canvas_img_path:
            self._canvas_img = cv.imread(canvas_img_path)
            if self._canvas_img is None:
                raise ImageNotFoundError(target_img_path)
        else:
            self._canvas_img = image_ops.color_like(self._target_img, (255, 255, 255))

        # Setup genetic algorithm
        # genes -> [stroke type, stroke x position, stroke y position, stroke scale, stroke rotation]
        genes = {
            'type': range(0, len(self._stroke_img_list)),
            'xPos': range(0, self._target_img.shape[1]),
            'yPos': range(0, self._target_img.shape[0]),
            # 'scale': {'low': 0.1, 'high': 1.0},
            'scale': {'low': 0.01, 'high': 1.0},
            'angle': {'low': 0.0, 'high': 360.0},
        }
        self._init_gene_tables(genes)

        # As it stands, multiprocessing is slower than running on a single core
        self._processes = 1

        # Setup PyGAD parameters
        genetic_config = config.genetic_algorithm
        self._ga_parameters = {
            'num_generations': genetic_config.generations,
            'fitness_func': lambda g, gidx: self._fitness_function(g, gidx),
            'sol_per_pop': genetic_config.population_size,
            'num_parents_mating': max(genetic_config.population_size // 4, genetic_config.population_size),
            'num_genes': len(self._gene_space),
            'gene_space': self._gene_space,
            'keep_elitism': genetic_config.keep_elitism,
            'parent_selection_type': 'sss',
            'crossover_type': 'uniform',
            'mutation_type': 'random',
            'mutation_probability': genetic_config.mutation_probability,
            'mutation_by_replacement': True,
        }

    def _init_gene_tables(self, genes: dict):
        gene_idx = 0
        self._gene_idx_table = {}
        for gene_name in genes.keys():
            self._gene_idx_table[gene_name] = gene_idx
            gene_idx += 1

        self._gene_space = list(genes.values())

    def _gene_idx(self, gene_name: str):
        return self._gene_idx_table[gene_name]

    def _image_from_gene(self, gene):
        # Select stroke
        stroke = self._stroke_img_list[int(gene[self._gene_idx('type')])].copy()

        # Scale stroke
        stroke = image_ops.scale_stroke(stroke, gene[self._gene_idx('scale')])
        # Rotate stroke
        stroke = image_ops.rotate_stroke(stroke, gene[self._gene_idx('angle')])

        position = (int(gene[self._gene_idx('xPos')]), int(gene[self._gene_idx('yPos')]))
        # Get stroke color
        color = image_ops.get_mean_stroke_color(self._target_img, stroke, position)
        # Draw stroke
        return image_ops.paint_stroke(self._canvas_img, stroke, color, position)

    def _fitness_function(self, gene, _gene_idx):
        diff = image_ops.image_difference(self._target_img, self._image_from_gene(gene))
        return 1 - diff

    def draw_stroke(self):
        # Create PyGAD instance since it is the only way or resetting the population
        if self._processes > 1:
            ga_instance = PooledGA(self._processes, **self._ga_parameters)
        else:
            ga_instance = pygad.GA(**self._ga_parameters)

        # Run said instance
        ga_instance.run()

        # Extract and paint the best stroke
        solution, solution_fitness, solution_idx = ga_instance.best_solution()
        self._canvas_img = self._image_from_gene(solution)

    def get_image(self):
        return self._canvas_img.copy()

    def store_image(self, output_file: str):
        if not cv.imwrite(output_file, self._canvas_img):
            raise OutputImageError(output_file)
