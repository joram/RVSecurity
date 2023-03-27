import React from 'react';
import { Outlet, Link } from "react-router-dom";
import './layout.css';
import {Menu} from "semantic-ui-react";

const Layout = () => {
  return (
    <div>
      <Menu>
          <Menu.Item as={Link} to="/">Home</Menu.Item>
          <Menu.Item as={Link} to="/contact">Contact</Menu.Item>
          <Menu.Item as={Link} to="/power">Power</Menu.Item>
      </Menu>
      <Outlet />
    </div>
    
    
  )
};

export default Layout;
