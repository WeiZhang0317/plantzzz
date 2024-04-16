import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import '../styles/QuizDetails.css';

const QuizDetails = () => {
  const { quizId } = useParams();
  const [quizDetails, setQuizDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    async function fetchQuizDetails() {
      setLoading(true);
      try {
        const response = await fetch(`http://localhost:5000/user/quiz/${quizId}`);
        const data = await response.json();
        // Ensure that true_false questions have proper options initialized
        data.questions.forEach(question => {
          if (question.questionType === 'true_false') {
            question.options = [
              { optionId: 'T', optionText: 'True', isCorrect: question.correctAnswer === 'T' },
              { optionId: 'F', optionText: 'False', isCorrect: question.correctAnswer === 'F' }
            ];
          }
        });
        setQuizDetails(data);
      } catch (error) {
        console.error('Failed to fetch quiz details:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchQuizDetails();
  }, [quizId]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'ArrowRight' && currentQuestionIndex < quizDetails.questions.length - 1) {
        changeQuestion(currentQuestionIndex + 1);
      } else if (event.key === 'ArrowLeft' && currentQuestionIndex > 0) {
        changeQuestion(currentQuestionIndex - 1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentQuestionIndex, quizDetails]);

  const changeQuestion = (newIndex) => {
    setCurrentQuestionIndex(newIndex);
    setSelectedOption(null);
    setFeedback(null);
  };

  const handleOptionSelect = (option) => {
    if (!option || !quizDetails) {
      console.error('Option or quiz details are undefined');
      return;
    }
    setSelectedOption(option);

    // Determine if the answer is correct based on question type
    const currentQuestion = quizDetails.questions[currentQuestionIndex];
    let isCorrect = false;

    if (currentQuestion.questionType === 'multi_choice') {
        isCorrect = option.isCorrect;  // multi_choice uses isCorrect flag on each option
    } else if (currentQuestion.questionType === 'true_false') {
        isCorrect = (option.optionText === 'True' && currentQuestion.correctAnswer === 'True') ||
                    (option.optionText === 'False' && currentQuestion.correctAnswer === 'False');
    }

    // Set feedback based on whether the selected option was correct
    setFeedback(isCorrect ? "Correct Answer!" : `Wrong Answer! Correct is: ${currentQuestion.correctAnswer}`);
};



  if (loading) return <div>Loading...</div>;
  if (!quizDetails || quizDetails.questions.length === 0) return <div>No quiz found!</div>;

  const question = quizDetails.questions[currentQuestionIndex];
  const totalQuestions = quizDetails.questions.length;
  const progress = (currentQuestionIndex + 1) / totalQuestions * 100;

  return (
    <div className="quiz-container">
      <h1>{quizDetails.quizName}</h1>
      <div className="progress-bar">
        <div className="progress-bar-fill" style={{ width: `${progress}%` }}>{Math.round(progress)}%</div>
      </div>
      <div className="question-card">
        <h3>{question.questionText}</h3>
        {question.imageUrl && <img src={question.imageUrl} alt={question.commonName} className="question-image" />}
        {question.options?.map((option) => (
          <button
            key={option.optionId}
            className={`option-button ${selectedOption?.optionId === option.optionId ? 'selected' : ''}`}
            onClick={() => handleOptionSelect(option)}
            disabled={selectedOption !== null}
          >
            {option.optionText}
          </button>
        ))}
        {feedback && (
          <div className={`feedback ${feedback.startsWith('Correct') ? 'correct' : 'incorrect'}`}>
            {feedback}
          </div>
        )}
      </div>
      <div className="navigation-buttons">
        <button onClick={() => changeQuestion(currentQuestionIndex - 1)} disabled={currentQuestionIndex === 0}>Previous</button>
        <button onClick={() => changeQuestion(currentQuestionIndex + 1)} disabled={currentQuestionIndex === totalQuestions - 1}>Next</button>
      </div>
    </div>
  );
};

export default QuizDetails;
