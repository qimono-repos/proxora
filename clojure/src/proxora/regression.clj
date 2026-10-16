(ns proxora.regression
  "A tiny, dependency-free ordinary least-squares regression example.")

(defn fit
  "Fit y = intercept + slope*x from observations [[x y] ...].
  Returns a map with :intercept and :slope."
  [observations]
  (when (< (count observations) 2)
    (throw (ex-info "Regression needs at least two observations"
                    {:observations observations})))
  (let [xs (map first observations)
        ys (map second observations)
        mean-x (/ (reduce + xs) (count xs))
        mean-y (/ (reduce + ys) (count ys))
        numerator (reduce + (map (fn [x y]
                                   (* (- x mean-x) (- y mean-y)))
                                 xs ys))
        denominator (reduce + (map (fn [x]
                                     (* (- x mean-x) (- x mean-x)))
                                   xs))]
    (when (zero? denominator)
      (throw (ex-info "Regression needs at least two distinct x values"
                      {:observations observations})))
    (let [slope (/ numerator denominator)]
      {:intercept (- mean-y (* slope mean-x))
       :slope slope})))

(defn predict
  "Predict y for x using a model returned by fit."
  [{:keys [intercept slope]} x]
  (+ intercept (* slope x)))

(defn predict-next
  "Treat a sequence as y-values at x = 0, 1, 2, ... and predict its next value."
  [values]
  (let [observations (mapv (fn [x y] [x y]) (range) values)
        model (fit observations)]
    (predict model (count values))))

(defn -main
  "Run the example: fit a line and predict the next sequence value."
  [& _]
  (let [observations [[0 1] [1 3] [2 5] [3 7]]
        model (fit observations)]
    (println "Observations:" observations)
    (println "Model:" model)
    (println "Prediction at x=4:" (predict model 4))
    (println "Next value for [1 3 5 7]:" (predict-next [1 3 5 7]))))
