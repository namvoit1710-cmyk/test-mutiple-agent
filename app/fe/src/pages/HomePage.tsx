import React from 'react';

// Placeholder for MainContainer
const MainContainer: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div>{children}</div>
);

const HomePage: React.FC = () => {
  return (
    <MainContainer>
      <h1>Home Page</h1>
      <p>Welcome!</p>
    </MainContainer>
  );
};

export default HomePage;
