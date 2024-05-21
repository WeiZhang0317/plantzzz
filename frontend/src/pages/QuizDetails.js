import React, { useCallback,useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useUserContext } from '../contexts/UserContext';
import { useQuiz } from '../contexts/QuizContext';
import '../styles/QuizDetails.css';
import { useNavigate } from 'react-router-dom';
import { CountdownCircleTimer } from 'react-countdown-circle-timer';

const questionTime = 20; 
// maximum 20s


const QuizDetails = () => {
  const { quizId } = useParams();
  const { user } = useUserContext();
  const navigate = useNavigate();
  const { saveResponse } = useQuiz();
  const [quizDetails, setQuizDetails] = useState(null);
  const [quizAnswers, setQuizAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [timer, setTimer] = useState(0);
  const timerRef = useRef(null);
  const [answers, setAnswers] = useState({});
  const [hasSavedProgress, setHasSavedProgress] = useState(false);
  const [showScoreModal, setShowScoreModal] = useState(false); // State to control the visibility of the score modal
  const [finalScore, setFinalScore] = useState(0); // State to store the final score
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [question, setQuestion] = useState({});
  const [progressing, setProgressing] = useState(false);
  const [showLightbox, setShowLightbox] = useState(false);
  const [lightboxImage, setLightboxImage] = useState('');
  const [showInstructions, setShowInstructions] = useState(true); // Add this state
  const [questionTimerKey, setQuestionTimerKey] = useState(0);
  // Add this state for resetting timer
  const [timeUp, setTimeUp] = useState(false);
   // Handlers for lightbox functionality
   const handleImageClick = (imageUrl) => {
    setShowLightbox(true);
    setLightboxImage(imageUrl);
  };

  const closeLightbox = () => {
    setShowLightbox(false);
  };

  useEffect(() => {
    const startTime = Date.now();
    timerRef.current = setInterval(() => {
      setTimer(Math.floor((Date.now() - startTime) / 1000)); // Update timer in seconds
    }, 1000);

    async function fetchQuizDetails() {
      setLoading(true);
      try {
        const response = await fetch(`http://localhost:5000/user/quiz/${quizId}/${user.studentId}`);
        const data = await response.json();
        const answers = {}
        data.answers.forEach(answer => {
          answers[answer.QuestionID] = answer
        });
        setQuizAnswers(answers);

        data.questions.forEach(question => {
          if (question.questionType === 'true_false') {
            question.options = [
              { optionId: 'T', optionText: 'True', isCorrect: question.correctAnswer === 'True' },
              { optionId: 'F', optionText: 'False', isCorrect: question.correctAnswer === 'False' }
            ];
          }
        });
        setQuizDetails(data);
        const question = data.questions[currentQuestionIndex]
        setQuestion(question)
        setProgressing(data.progressing)
        if (question && answers && answers[question.questionId] && data.progressing) {
          handleOptionSelect({optionId: answers[question.questionId].SelectedOptionID, isCorrect: answers[question.questionId].IsCorrect}, data)
        }
      } catch (error) {
        console.error('Failed to fetch quiz details:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchQuizDetails();
    return () => clearInterval(timerRef.current);
  }, [quizId]);


  const changeQuestion = useCallback((newIndex) => {
    setCurrentQuestionIndex(newIndex);
    const currentQuestion = quizDetails.questions[newIndex]
    setQuestion(currentQuestion)
    const questionId = currentQuestion.questionId;

     setQuestionTimerKey(prevKey => prevKey + 1); // Reset timer by changing the key
     setTimeUp(false); 

    if (answers[questionId]) {
      setSelectedOption(answers[questionId].selectedOptionId);
      setFeedback(answers[questionId].feedback);
    } else {
      setSelectedOption(null);
      setFeedback(null);
    }
    console.warn(progressing, 111)
    if (quizAnswers[questionId] && progressing) {
      handleOptionSelect({optionId: quizAnswers[questionId].SelectedOptionID, isCorrect: quizAnswers[questionId].IsCorrect})
    }
  }, [quizDetails, answers]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'ArrowRight' && currentQuestionIndex < quizDetails?.questions.length - 1) {
        changeQuestion(currentQuestionIndex + 1);
      } else if (event.key === 'ArrowLeft' && currentQuestionIndex > 0) {
        changeQuestion(currentQuestionIndex - 1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
}, [currentQuestionIndex, quizDetails, changeQuestion]);

const handleProgressBarClick = (e) => {
  const progressBar = e.currentTarget;
  const clickPosition = e.nativeEvent.offsetX;
  const progressBarWidth = progressBar.offsetWidth;
  const clickPercentage = clickPosition / progressBarWidth;
  const questionIndex = Math.floor(clickPercentage * quizDetails.questions.length);
  changeQuestion(questionIndex);
};




  const handleOptionSelect = (option, initQuizDetails) => {
  const details = quizDetails || initQuizDetails
  if (!option || !details) {
    console.error('Option or quiz details are undefined');
    return;
  }

  setSelectedOption(option);
  const currentQuestion = details.questions[currentQuestionIndex];
  const isCorrect = option.isCorrect;

  // Save response locally
  saveResponse({
    questionId: currentQuestion.questionId,
    selectedOptionId: option.optionId,
    isCorrect
  });
  // Update local answers state
  setAnswers(prev => ({
    ...prev,
    [currentQuestion.questionId]: {
      questionId: currentQuestion.questionId,
      selectedOptionId: option.optionId,
      isCorrect: isCorrect,
      feedback: isCorrect ? "Correct Answer!" : `Wrong Answer! Correct is: ${currentQuestion.correctAnswer}`
    }
  }));

  setSelectedOption(option.optionId);
  setFeedback(isCorrect ? "Correct Answer!" : `Wrong Answer! Correct is: ${currentQuestion.correctAnswer}`);
};





const saveProgress = async () => {
  if (!isSubmitted) {
    try {
      const response = await fetch(`http://localhost:5000/user/save-progress/${quizId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          studentId: user.studentId,
          answers: Object.values(answers)  // Assuming this sends only new answers or is managed accordingly on the backend
        })
      });

      const data = await response.json();
      if (data) {
        setHasSavedProgress(true);  // Enable the submit button after progress is saved
        alert(data.message);  // Show backend message
      }
    } catch (error) {
      console.error('Failed to save progress:', error);
      alert('Failed to save progress');
    }
  }
};



const submitQuiz = async () => {
  try {
    const response = await fetch(`http://localhost:5000/user/submit-quiz/${quizId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        studentId: user.studentId
      })
    });

    const data = await response.json();
    setFinalScore(data.final_score); // Store the final score received from the backend
    setShowScoreModal(true); // Show the score modal
    setIsSubmitted(true); // Prevent further modifications
    setAnswers({}); // Optionally clear answers to prevent reuse in the UI
  } catch (error) {
    console.error('Failed to submit quiz:', error);
    alert('Failed to submit quiz');
  }
};






  if (loading) return <div>Loading...</div>;
  if (!quizDetails || quizDetails.questions.length === 0) return <div>No quiz found!</div>;

  const totalQuestions = quizDetails.questions.length;
  const progress = (currentQuestionIndex + 1) / totalQuestions * 100;
  const baseUrl = 'http://localhost:5000/static/';      
        
  
  return (
    <div className="quiz-container">

    {showInstructions && (
      <div className="modal-backdrop">
        <div className="score-modal">
          <h2>Instructions</h2>
          <p>Questions 1-50 are True/False.</p>
          <p>Questions 51-100 are multiple-choice.</p>
          <p>You can click "Save Progress" to save your progress and continue later, but note that the total time spent will affect your ranking. Click "Submit Quiz" to submit your results to the leaderboard.</p>
          <button onClick={() => setShowInstructions(false)}>I Understand</button>
        </div>
      </div>
    )}


<div className="quiz-header">
  <h1>{quizDetails.quizName}</h1>
  <div className="time-elapsed">
    {!timeUp ? (
      <CountdownCircleTimer
      key={questionTimerKey}
      isPlaying
      duration={questionTime}
      colors={['#4CAF50', '#F7B801', '#A30000']}
      colorsTime={[30, 15, 0]}
      onComplete={() => {
        setTimeUp(true);
        return { shouldRepeat: false, delay: 1 };
      }}
      size={189} /* Adjust the size if the component supports this prop for direct sizing */
      style={{
        width: '100%',  /* Ensures that the timer fills its container */
        height: '100%',
      }}
    >
      {({ remainingTime }) => (
        <div className="timer">{remainingTime}</div>
      )}
    </CountdownCircleTimer>
    ) : (
      <div className="bubble" style={{ 
        backgroundColor: '#fff', 
        borderRadius: '25px', 
        padding: '10px 20px', 
        boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100%', 
        textAlign: 'center' 
      }}>
        <div className="bubble-text" style={{ fontSize: '14px', color: '#f44336' }}>You should be faster, keep it up!</div>
      </div>
    )}
  </div>
</div>

      <div className="progress-bar" onClick={handleProgressBarClick}>
        <div className="progress-bar-fill" style={{ width: `${progress}%` }}>{Math.round(progress)}%</div>
      </div>
      {question && question.questionId ? <div className="question-card">
        <h3>{question.questionText}</h3>
        {question.imageUrl && (
          <img 
            
            src={`${baseUrl}${question.imageUrl}`} 
            alt={question.commonName} 
            className="question-image"
            onClick={() => handleImageClick(`${baseUrl}${question.imageUrl}`)}
          />
        )}
        {question.options?.map((option) => (
            <button
                key={option.optionId}
                className={`option-button ${selectedOption?.optionId === option.optionId ? 'selected' : ''}`}
                onClick={() => handleOptionSelect(option)}
                disabled={selectedOption !== null || isSubmitted}  // Disable if an option is already selected or if the quiz is submitted
            >
              {option.optionLabel ? `${option.optionLabel}. ${option.optionText}` : option.optionText}
            </button>
        ))}
        {feedback && (
            <div className={`feedback ${feedback.startsWith('Correct') ? 'correct' : 'incorrect'}`}>
              {feedback}
            </div>
        )}
         {/* Lightbox Overlay */}
         {showLightbox && (
        <div className="lightbox-overlay" onClick={closeLightbox}>
          <img src={lightboxImage} alt="Enlarged view" className="lightbox-image" />
          <button onClick={closeLightbox} className="lightbox-close">Close</button>
        </div>
      )}


      </div> : ''}
      <div className="navigation-buttons">
      <button onClick={() => changeQuestion(currentQuestionIndex - 1)} disabled={currentQuestionIndex === 0 || isSubmitted}>Previous</button>
      <button onClick={() => changeQuestion(currentQuestionIndex + 1)} disabled={currentQuestionIndex === totalQuestions - 1 || isSubmitted}>Next</button>
      <button onClick={saveProgress} className="save-progress-button" disabled={isSubmitted}>Save Progress</button>
      <button onClick={submitQuiz} className="submit-quiz-button" disabled={!hasSavedProgress || isSubmitted}>Submit Quiz</button>

      </div>
      {showScoreModal && (
        <div className="score-modal">
          <h2>Your Final Score: {finalScore}</h2>
          <button onClick={() => {
            setShowScoreModal(false);
            navigate('/student/dashboard/all-quizzes');
          }}>Back to Quiz Page</button>
        </div>
      )}
    </div>
  );


};

export default QuizDetails;
