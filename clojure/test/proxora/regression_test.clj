(ns proxora.regression-test
  (:require [clojure.test :refer [deftest is testing run-tests]]
            [proxora.regression :as regression]))

(deftest fits-a-perfect-line
  (testing "ordinary least squares recovers y = 1 + 2x"
    (let [model (regression/fit [[0 1] [1 3] [2 5] [3 7]])]
      (is (= 1 (:intercept model)))
      (is (= 2 (:slope model)))
      (is (= 9 (regression/predict model 4))))))

(deftest predicts-next-sequence-value
  (is (= 9 (regression/predict-next [1 3 5 7]))))

(deftest rejects-too-few-observations
  (is (thrown? clojure.lang.ExceptionInfo
               (regression/fit [[0 1]]))))

(deftest rejects-identical-x-values
  (is (thrown? clojure.lang.ExceptionInfo
               (regression/fit [[2 1] [2 3]]))))

(defn -main [& _]
  (let [result (run-tests 'proxora.regression-test)]
    (when (pos? (+ (:fail result) (:error result)))
      (System/exit 1))))
