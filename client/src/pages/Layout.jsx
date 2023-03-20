import React from 'react';
import { Outlet, Link } from "react-router-dom";
import './layout.css';

const Layout = () => {
  return (
    <div>
      <nav>
        <ul>
          <li>
            <Link to="/">Home</Link>
          </li>
          <li>
            <Link to="/contact">Contact</Link>
          </li>
          <li>
            <Link to="/power">Power - real power page</Link>
          </li>
        </ul>
      </nav>
      <div className='button2'>
        <button type="button">Click Me</button>
      </div>
      <Outlet />
    </div>
    
    
  )
};

export default Layout;
