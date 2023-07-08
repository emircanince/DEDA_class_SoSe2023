import gensim
from gensim.models import CoherenceModel, LdaSeqModel 
import pyLDAvis.gensim_models as gensimvis
import pyLDAvis
import matplotlib.pyplot as plt
import pandas as pd
import csv
import numpy as np
import os

class LDA:
    '''
    A custom LDA interface designed to carry out a grid search, find the best model and vizualize it. 
    Dynamic topic modelling can be also done if grid search is carried out first. 
    
    Args:
    
        corpus: A bag of words corpus (Already generated by CorpusMaker)
        dictionary: A gensim dictionary (Already generated by CorpusMaker)
        texts: All tokens (Already generated by CorpusMaker)
        dates: All dates of the papers (Already generated by CorpusMaker
        
    How to use:
        
        MSc_LDA = LDA(corpus, dictionary, texts) <-- initializes the class
        m = MSc_LDA.simple_fit() <-- fits one model with custom specs
        MSc_LDA.grid_search(n_topics, alphas, betas) <-- conducts grid search
        MSc_LDA.lineplot_scores() <-- plots coherence scores from grid search rounds
        m = MSc_LDA.build_best_model() <-- fits best model
        MSc_LDA.viz() <-- vizualizes best/simple model
        MSc_LDA.time_slicer(year_batches) <-- prepares date input for DTM
        MSc_LDA.DTM() <-- builds the dynamic model assuming grid search for LDA has been carried out
    
    '''
    
    def __init__ (self, corpus, dictionary, texts, dates):
        
        # Below the usual def __init__ items: Those selected by the user
        self.corpus = corpus
        self.dictionary = dictionary
        self.texts = texts
        self.dates = dates
        
        # Simple fit model item, set to None at initialization
        self.simple_model = None
        
        # Below the grid search items, that will get overwritten per search iteration
        # Set to none because it gets selected by the algorithm
        self.best_params = None
        
        # Since coherence score ranges from 0 to 1, we should initialize the best score as as anything below 0
        self.best_score = -1
        
        # Set to none due to reason mentioned
        self.best_model = None
        
        # Set to none
        self.time_slice = None
        
        
    def get_coherence_score(self, n, alpha, beta):
        
        '''
        Calculates the coherence score per model using gensim's CoherenceModel.
        
        Args:
            n: Number of topics in one LDA model (per iteration of search)
            alpha: Document-Topic Density
            beta: Topic-Word Density
            
        Returns:
            Coherence score, fitted LDA model.
            
        '''
        
        m = gensim.models.LdaModel(corpus = self.corpus,
                                   id2word = self.dictionary,
                                   num_topics = n,
                                   random_state = 66,  # Custom random state used in our project
                                   update_every = 1,
                                   chunksize = 100,
                                   passes = 10,
                                   alpha = alpha, # Alpha grabbed from function arguments
                                   per_word_topics = True,
                                   eta = beta # beta grabbed from function arguments
        )
        
        cm = CoherenceModel(model = m,
                            texts = self.texts,
                            corpus = self.corpus,
                            dictionary = self.dictionary,
                            coherence = 'c_v'
                           )
        
        # Returns the variables defined above
        # This comes in handy when fitting the best model after grid search
        return cm.get_coherence(), m
        
    def simple_fit(self, n_top, alpha_val, beta_val):
        '''
        Fits a "simple" LDA model, without any grid search.
        
        Args:
            n_top: The number of topics 
            alpha_val: Document-Topic Density
            beta_val: Topic-Word Density.
        
        Returns:
            Fitted LDA model.
            
        '''
        
        # Set up LDA model
        model = gensim.models.LdaModel(corpus = self.corpus,
                                   id2word = self.dictionary,
                                   num_topics = n_top,
                                   random_state = 66,  # Custom random state used in our project
                                   update_every = 1,
                                   chunksize = 100,
                                   passes = 10,
                                   alpha = alpha_val, 
                                   per_word_topics = True,
                                   eta = beta_val) 
        
        
        # Get coherence score
        coh_model = CoherenceModel(model = model, texts = self.texts, corpus = self.corpus, dictionary = self.dictionary, coherence = 'c_v')
        coherence = coh_model.get_coherence()
        
        # Get perplexity
        perplexity = model.log_perplexity(self.corpus)
        
        print(f'\nCoherence Score is: {coherence}')
        print(f'\nPerplexity Score is: {perplexity}')
        print('\nSee the topics:')
        topics = model.print_topics()
        for topic in topics:
            print(topic)
            
        # Save as CSV via pandas
        simple_topics_df = pd.DataFrame(topics, columns = ['Topic N', 'Words'])
        
        # We specify saving path and make sure to create it if it does not exist
        if not os.path.exists('Topics_CSVs'):
            os.makedirs('Topics_CSVs')
        
        simple_topics_df.to_csv(os.path.join('Topics_CSVs', 'Topics_from_simple_model.csv'), index = False)
        
        # We specify saving path and make sure to create it if it does not exist
        if not os.path.exists('LDAModels_Gensim'):
            os.makedirs('LDAModels_Gensim')
        
        
        model.save(os.path.join('LDAModels_Gensim', 'MSc_LDA_simple.gensim'))
        
        # Add as self attribute to be used in viz later
        self.simple_model = model
        
        return model
    
    def grid_search(self, n_topics, alphas, betas, verbose = False):
        
        '''
        Performs grid search, finding optimal LDA parameters
        
        Args:
            n_topics: list of possible topic number (can use list(range( ,)))
            alphas: list of alpha values (can use np.arange( , , ).tolist())
            betas: list of beta values (can use np.arange( , , ).tolist())
            verbose: If set to true, will give information about the number of topics, alpha and beta values and their coherence score per iteration

        Returns:
            self.scores: Coherence and perplexity scores for all LDA models tried out in grid search. 
        '''
        # Empty container for scores
        self.scores = []
        # Begin loop
        for n in n_topics:
            for alpha in alphas:
                for beta in betas:
                    
                    # Get coherence score and model
                    coherence_score, model = self.get_coherence_score(n, alpha, beta)
                    # Get perplexity score from model
                    perplexity_score = model.log_perplexity(self.corpus)
                    
                    # Append into empty container for scores
                    self.scores.append({'n_topics': n,
                                        'alpha': alpha,
                                        'beta': beta,
                                        'coherence_score': coherence_score,
                                        'perplexity_score': perplexity_score,
                       })
                    
                    # The if statement will always be valid in the first iteration
                    # but it will give the best score at the end of the run
                    
                    if coherence_score > self.best_score:
                        self.best_score = coherence_score
                        self.best_params = (n, alpha, beta)
                        self.best_model = model
                    
                    # This gives a very long print output in case of large grid search
                    # so it is only activated if verbose = True
                    if verbose:
                        print(f'\nNumber of topics: {n}; alpha: {alpha}; beta: {beta}; Achieved coherence score: {coherence_score}')
                        
        scores_df = pd.DataFrame(self.scores)
        
        # Same statement as above for saving directory
        if not os.path.exists('Topics_CSVs'):
            os.makedirs('Topics_CSVs')
        
        scores_df.to_csv(os.path.join('Topics_CSVs', 'scores_from_search.csv'), index = False)
        
        
    def lineplot_scores(self):
        '''
        Constructs line plot with number of topics in LDA model on X axis and respective coherence and peplexity scores on Y axis.
        '''
  
        # Plot configuration 
        plt.style.use('seaborn-v0_8-white')
        plt.rcParams['figure.figsize'] = [12, 6.75]
        plt.rcParams['font.size'] = 24

        # Use list comprehension to extract the variables we need for plotting 
        topics = [n_topic['n_topics'] for n_topic in self.scores]
        coherence_scores = [score['coherence_score'] for score in self.scores]
        perplexity_scores = [score['perplexity_score'] for score in self.scores]
            
        # Initialize subplots
        fig1, ax1 = plt.subplots()
            
        ax1.set_xlabel('Number of Topics')
        ax1.set_ylabel('Coherence Score')
        ax1.plot(topics, coherence_scores)
        fig1.tight_layout()
        if not os.path.exists('Plots'):
            os.makedirs('Plots')
        plt.savefig(os.path.join('Plots', 'Coherence_Scores.png'), dpi = 300, transparent = True)
        plt.show()
        plt.close()
            
        fig2, ax2 = plt.subplots()       
        ax2.set_xlabel('Number of Topics')
        ax2.set_ylabel('Perplexity')
        ax2.plot(topics, perplexity_scores)
            
        fig2.tight_layout()
        if not os.path.exists('Plots'):
            os.makedirs('Plots')
        plt.savefig(os.path.join('Plots', 'Perplexity_Scores.png'), dpi = 300, transparent = True)        
        plt.show()
        plt.close()
        
         
        
    
    def build_best_model(self):
        
        '''
        Fits the best model found during the grid search.
        
        Returns:
            The LDA model.
        '''
        
        # A neat line of if statetement included as a flex
        if self.best_params:
            n, alpha, beta = self.best_params
            
            # We do not need the coherence score so leave first blank
            _, model = self.get_coherence_score(n, alpha, beta)
            
            # Save the model to be able to load it via Gensim later
            if not os.path.exists('LDAModels_Gensim'):
                os.makedirs('LDAModels_Gensim')
                    
            model.save(os.path.join('LDAModels_Gensim', 'Grid_Best_MSc_LDA.gensim'))
            
            
            topics = model.print_topics()
            for t in topics:
                print(t)
                
            # Further save the topics as a csv
            if not os.path.exists('Topics_CSVs'):
                os.makedirs('Topics_CSVs')

            
            with open(os.path.join('Topics_CSVs', 'best_topics.csv'), 'w', newline = '') as f:
                writer = csv.writer(f)
                writer.writerow(['Topic N', 'Keywords'])
                for t in topics:
                    writer.writerow(t)
                    
            return model
         
        else:
            raise Exception('No parameters found for the best model. Make sure you have run the grid search already.')

    
    def viz(self, model_type = 'best'):
        
        '''
        Visualizes the optimal LDA model found by gridsearch using pyLDAvis
        
        Args:
            model_type: Specify whether we want the visualization for the model trained through simple_fit method or through the build_best_model (via grid search). Default: best
        
        Returns:
            The visualizations
        '''
        if model_type == 'best':
            model = self.best_model
            if model is None:
                raise Exception('No best model found. Run grid_search first.')
        
        elif model_type == 'simple':
            model = self.simple_model
            if model is None:
                raise Exception('No simple model found. Run simple_fit() first.')
        
        else:
            raise ValueError('Model type not valid. Please select either "best" or "simple".')
        
        # Visualize using pyLDAvis
        pyLDAvis.enable_notebook()
        viz = gensimvis.prepare(model, self.corpus, self.dictionary)
        
        
        # Save the visualization as HTML
        plot_directory = 'Plots'
        if not os.path.exists(plot_directory):
            os.makedirs(plot_directory)
            
        html_path = os.path.join(plot_directory, f'lda_{model_type}_viz.html')
        pyLDAvis.save_html(viz, html_path)
        
        return viz
   
    def time_slicer(self, year_batches):
        '''
        Takes a list of several year ranges and converts them into time slices as an input for dtm.
        
        Args:
            year_batches: List of several year ranges
        Returns:
            time_slice: input for dtm
            
        Example use:
            Set up variable: 
                year_batches = [range(2002,2009), range(2009,2016), range(2016, 2020), range(2020, 2024)]
            Run method:
                time_slicer(year_btaches)

        '''
        year_counts = {}
        for item in self.dates:
            year = item[0]
            if year in year_counts:
                year_counts[year] += 1
            else:
                year_counts[year] = 1
        
        
        year_batches = [list(item) for item in year_batches]
        batches_counts = {}
        for index, year_batch in enumerate(year_batches):
            batches_counts[index] = 0

        for key, value in year_counts.items():
            for index, batch in enumerate(year_batches):
                if int(key) in batch:
                    batches_counts[index] += value
        self.time_slice = list(batches_counts.values())
        
        time_slice = self.time_slice
        
        return time_slice
    
    
    def DTM(self, year_batches):
        '''
        Builds a DTM model following the best parameters received from grid_search. Note: function will not work without conducting a grid search.
        
        Inputs:
            year_batches: List of several year ranges
        Returns:
            Sequential model
        '''
        
        print('\nThe model is being built. This may take some time...')

        # Specify model
        seq_m = LdaSeqModel(corpus = self.corpus, id2word = self.dictionary, time_slice = self.time_slice,  num_topics = self.best_params[0], alphas = self.best_params[1], initialize = 'ldamodel', lda_model = self.best_model, random_state = 66)
        
        
        if not os.path.exists('LDAModels_Gensim'):
            os.makedirs('LDAModels_Gensim')
        # Save model in directory            
        seq_m.save(os.path.join('LDAModels_Gensim', 'DTM_model.gensim'))
        
        print('\nThe model successfully built. Currently processing its output...')
        # Empty container for model's output topics
        DTM_topics = []
        
        # Iterate and append
        for topic in range(0, self.best_params[0]):
            DTM_topics.append(seq_m.print_topic_times(topic = topic, top_terms = 30))
        
        # Turn year batches from a list to a string "begin_year - end_year"
        time_periods = [f'{period[0]}-{period[-1]}' for period in year_batches]
        
        # Small function to take an element of DTM_topics and turn it into dataframe
        def topic_time(DTM_topic, time_periods):  
            dfs = []
            for period, topic_dist in enumerate(DTM_topic):
                df = pd.DataFrame(topic_dist, columns=["Word", f"Period {period+1}"])
                dfs.append(df)

            # Merge the DataFrames based on the "Word" column
            topic_words_time = pd.concat(dfs).groupby("Word").sum()

            # Fill NaN values with zeros
            topic_words_time.fillna(0, inplace=True)
            topic_words_time.columns = time_periods

            # Display the resulting DataFrame
            return topic_words_time
        
        topics_words_time = []

        for topic in DTM_topics:
            topics_words_time.append(topic_time(topic,time_periods))
        
        directory = 'Topics_CSVs/topics_words_time'
        # Set up folder to save topics
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Iterate over each element in topics_words_time
        for i, df in enumerate(topics_words_time):
            # Generate file path for current topic
            file_path = os.path.join(directory, f"topic{i+1}_words_time.csv")
            # Save the dataframe as a CSV file
            df.to_csv(file_path)
            
        print('\nAll done!')
        
    def DTM_upload(self, year_batches):
        '''
        An alternative method that will process pre-built DTM model.
       
        Inputs:
            year_batches: List of several year ranges
        Returns:
            Sequential model
        '''
        
        seq_m = LdaSeqModel.load('LDAModels_Gensim/DTM_model.gensim') 
        #seq_m.save(os.path.join('LDAModels_Gensim', 'DTM_model.gensim'))
        
        print('\nThe model successfully built. Currently processing its output...')
        # Empty container for model's output topics
        DTM_topics = []
        
        # Iterate and append
        for topic in range(0, self.best_params[0]):
            DTM_topics.append(seq_m.print_topic_times(topic = topic, top_terms = 30))
        
        # Turn year batches from a list to a string "begin_year - end_year"
        time_periods = [f'{period[0]}-{period[-1]}' for period in year_batches]
        
        # Small function to take an element of DTM_topics and turn it into dataframe
        def topic_time(DTM_topic, time_periods):  
            dfs = []
            for period, topic_dist in enumerate(DTM_topic):
                df = pd.DataFrame(topic_dist, columns=["Word", f"Period {period+1}"])
                dfs.append(df)

            # Merge the DataFrames based on the "Word" column
            topic_words_time = pd.concat(dfs).groupby("Word").sum()

            # Fill NaN values with zeros
            topic_words_time.fillna(0, inplace=True)
            topic_words_time.columns = time_periods

            # Display the resulting DataFrame
            return topic_words_time
        
        topics_words_time = []

        for topic in DTM_topics:
            topics_words_time.append(topic_time(topic,time_periods))
        
        directory = 'Topics_CSVs/topics_words_time'
        # Set up folder to save topics
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Iterate over each element in topics_words_time
        for i, df in enumerate(topics_words_time):
            # Generate file path for current topic
            file_path = os.path.join(directory, f"topic{i+1}_words_time.csv")
            # Save the dataframe as a CSV file
            df.to_csv(file_path)
            
        print('\nAll done!')

        
        return seq_m
        
        
    def DTM_Plot(self, k = 5, topic_folder = None): 
        """
        Method to make plots of the topic over time output of DTM
        
        Args:
            k: integer, number of top words to visualize per topic. By default set to 5
            topic folder: Directory that contains topics saved as CSV files by the sequential model
        Returns:
            Plots
        """
    
        # To access the entries in the topics_word_time folder
        files = os.listdir(topic_folder)
        topics_words_time = [pd.read_csv(os.path.join(topic_folder, file), index_col=0) for file in files]
        # Empty container for 
        top_k_words_topics_overtime = []
        
        #takes top k words from the dataframe for each topic
        # if the top k changes over periods, it includes all words that have ever been in top k
        for topic_df in topics_words_time:
            topic_topk_words = set()
            for period in topic_df.columns:
                #gets top 5 words for each period
                topic_topk_words_in_period = list(topic_df[period].sort_values(ascending=False)[:k].index)
                topic_topk_words.update(topic_topk_words_in_period)
                
            top_k_words_topics_overtime.append(topic_df[topic_df.index.isin(topic_topk_words)])
            
            
        for index, topic in enumerate(top_k_words_topics_overtime, start = 1):
            # Plotting parameters
            plt.style.use('seaborn-v0_8-white')
            plt.rcParams['figure.figsize'] = [14.4, 8.1]
            plt.rcParams['font.size'] = 24
            plt.title(f'Topic {index}: 5 Most Wrequent Words Over Time')
            plt.xlabel('Period')
            plt.ylabel('Word Frequency')

            # Iterate over each word
            for word in topic.index:
                frequencies = topic.loc[word].values
                plt.plot(topic.columns, frequencies, label=word)
                plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

            plt.tight_layout()    
            plt.savefig(f'Plots/topic{index}_evolution.png', dpi = 300, transparent = True)
            plt.show()
            plt.close()